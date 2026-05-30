"""Pytest configuration and shared fixtures."""
import pytest
from models.state import State
from models.transition import Transition
from models.rule import Rule
from carla_bindings import LazyDict


@pytest.fixture
def idle_state():
    """Create a reusable idle state."""
    return State("idle")


@pytest.fixture
def warning_state():
    """Create a reusable warning state."""
    return State("warning")


@pytest.fixture
def violation_state():
    """Create a reusable violation state."""
    return State("violation")


@pytest.fixture
def dummy_rule(idle_state, warning_state):
    """Create a simple two-state rule for testing."""
    return Rule(
        name="Test Rule",
        constants={"threshold": 10},
        transitions=[
            Transition(condition="value > threshold", source=idle_state, target=warning_state),
            Transition(condition="value <= threshold", source=warning_state, target=idle_state),
        ],
    )
