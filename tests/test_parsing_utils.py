"""Tests for YAML rule parsing."""
import pytest
from utils.parsing_utils import parse_rule_file, parse_yaml


def test_parse_lane_keeping_rule_basic():
    """Parsing lane_keeping_continuous.yaml produces expected rule object."""
    rule = parse_rule_file("./admin/rules/lane_keeping_continuous.yaml")
    assert rule is not None, "Rule should not be None"
    assert rule.name == "lane_keeping_continuous", f"Expected name 'lane_keeping_continuous', got {rule.name}"


def test_parse_lane_keeping_rule_constants():
    """Parsing includes metadata constants."""
    rule = parse_rule_file("./admin/rules/lane_keeping_continuous.yaml")
    assert isinstance(rule.constants, dict), "Constants should be a dict"
    assert "warning_threshold" in rule.constants, "Should have warning_threshold constant"
    assert (
        float(rule.constants["warning_threshold"]) == 0.5
    ), "warning_threshold should be 0.5"


def test_parse_lane_keeping_rule_transitions_count():
    """Parsing produces expected number of transitions."""
    rule = parse_rule_file("./admin/rules/lane_keeping_continuous.yaml")
    # YAML has 5 transitions; parser ignores '[*]' entry, so we expect 4
    assert len(
        rule._transitions) == 4, f"Expected 4 transitions, got {len(rule._transitions)}"


def test_parse_lane_keeping_rule_transition_targets():
    """Parsing creates expected state transitions."""
    rule = parse_rule_file("./admin/rules/lane_keeping_continuous.yaml")
    target_names = {t.target.name for t in rule._transitions}
    assert "warning" in target_names, "Should have transitions to 'warning' state"
    assert "violation" in target_names, "Should have transitions to 'violation' state"
    assert "idle" in target_names, "Should have transitions to 'idle' state"


def test_parse_lane_keeping_rule_violation_condition():
    """Parsing includes condition that checks line_continuous status."""
    rule = parse_rule_file("./admin/rules/lane_keeping_continuous.yaml")
    conditions = [t.condition for t in rule._transitions]
    assert any(
        "line_continuous" in (c or "") for c in conditions
    ), "Should have condition checking line_continuous"


def test_parse_nonexistent_file_returns_none():
    """Parsing non-existent file returns None."""
    rule = parse_rule_file("./nonexistent.yaml")
    assert rule is None, "Should return None for missing file"


def test_parse_yaml_basic():
    """parse_yaml handles basic YAML content."""
    yaml_content = """key1: value1
key2: 42"""
    result = parse_yaml(yaml_content)
    assert result["key1"] == "value1"
    assert result["key2"] == 42


def test_parse_yaml_invalid_returns_empty():
    """parse_yaml returns empty dict on invalid YAML."""
    invalid_yaml = """:invalid: :yaml: :syntax:"""
    result = parse_yaml(invalid_yaml)
    assert result == {}, "Should return empty dict for invalid YAML"
