"""Tests for ViolationLogger buffering and file I/O."""
import json
from pathlib import Path
import pytest
from utils.violation_logger import ViolationLogger


class DummyObject:
    """Simple object for testing serialization of complex scene data."""

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return f"DummyObject({self.value})"


def test_violation_logger_autoflush_on_buffer_full(tmp_path):
    """ViolationLogger auto-flushes when buffer reaches buffer_size."""
    log_dir = tmp_path / "logs"
    vl = ViolationLogger(log_dir=str(log_dir), buffer_size=2)

    # First violation stays in buffer
    vl.log_violation("rule1", 1, {"speed": 50})
    assert len(vl.buffer) == 1, "Buffer should have 1 entry"
    assert not Path(vl.log_file).exists(), "File should not exist yet"

    # Second violation triggers flush
    vl.log_violation("rule2", 2, {"speed": 60})
    assert len(vl.buffer) == 0, "Buffer should be empty after autoflush"
    assert Path(vl.log_file).exists(), "Log file should be created"

    # Verify file contents
    lines = Path(vl.log_file).read_text().splitlines()
    assert len(lines) == 2, "Should have 2 entries in file"
    entry = json.loads(lines[0])
    assert entry["rule"] == "rule1"
    assert entry["frame"] == 1


def test_violation_logger_serializes_complex_objects(tmp_path):
    """ViolationLogger converts objects to strings for serialization."""
    log_dir = tmp_path / "logs2"
    vl = ViolationLogger(log_dir=str(log_dir), buffer_size=10)  # larger buffer to prevent immediate flush
    vl.log_violation("test", 5, {"obj": DummyObject(42)})

    assert len(vl.buffer) == 1
    entry = vl.buffer[0]
    assert entry["scene"]["obj"] == "DummyObject(42)"


def test_violation_logger_manual_flush(tmp_path):
    """ViolationLogger flushes on explicit flush() call."""
    log_dir = tmp_path / "logs3"
    vl = ViolationLogger(log_dir=str(log_dir), buffer_size=10)
    vl.log_violation("r", 7, {"k": "v"})
    assert len(vl.buffer) == 1

    vl.flush()
    assert len(vl.buffer) == 0, "Buffer should be empty after flush"
    assert Path(vl.log_file).exists()
    lines = Path(vl.log_file).read_text().splitlines()
    assert len(lines) == 1


def test_violation_logger_flush_noop_on_empty(tmp_path):
    """ViolationLogger.flush() does nothing when buffer is empty."""
    log_dir = tmp_path / "logs4"
    vl = ViolationLogger(log_dir=str(log_dir), buffer_size=5)
    vl.flush()  # Should not raise or create file
    assert not Path(vl.log_file).exists(), "File should not be created on empty flush"


def test_violation_logger_appends_to_existing_file(tmp_path):
    """Multiple flushes append to the same log file."""
    log_dir = tmp_path / "logs5"
    vl = ViolationLogger(log_dir=str(log_dir), buffer_size=1)

    vl.log_violation("r1", 1, {"x": 1})
    vl.flush()
    vl.log_violation("r2", 2, {"x": 2})
    vl.flush()

    lines = Path(vl.log_file).read_text().splitlines()
    assert len(lines) == 2, "Should have 2 entries total"
    assert json.loads(lines[0])["rule"] == "r1"
    assert json.loads(lines[1])["rule"] == "r2"
