"""Tests for Transition guard evaluation."""
import pytest
from models.transition import Transition
from models.state import State
from carla_bindings import LazyDict


def test_transition_verify_true(idle_state, warning_state):
    """Transition.verify returns True when condition matches."""
    t = Transition(condition="x == 5", source=idle_state, target=warning_state)
    assert t.verify(LazyDict({"x": 5})) is True, "Transition should verify when condition is true"


def test_transition_verify_false(idle_state, warning_state):
    """Transition.verify returns False when condition does not match."""
    t = Transition(condition="x == 5", source=idle_state, target=warning_state)
    assert t.verify(LazyDict({"x": 4})) is False, "Transition should not verify when condition is false"


def test_transition_verify_complex_condition(idle_state, warning_state):
    """Transition.verify handles complex boolean expressions."""
    t = Transition(
        condition="x > 10 and y < 20",
        source=idle_state,
        target=warning_state,
    )
    assert t.verify(LazyDict({"x": 15, "y": 10})) is True
    assert t.verify(LazyDict({"x": 5, "y": 10})) is False
    assert t.verify(LazyDict({"x": 15, "y": 25})) is False


def test_transition_verify_missing_key_raises(idle_state, warning_state):
    """Transition.verify raises NameError when referenced variable is missing."""
    t = Transition(condition="x == 5", source=idle_state, target=warning_state)
    with pytest.raises(NameError):
        t.verify(LazyDict({}))


def test_transition_repr(idle_state, warning_state):
    """Transition has readable repr showing condition and states."""
    t = Transition(condition="speed > 50", source=idle_state, target=warning_state)
    repr_str = repr(t)
    assert "speed > 50" in repr_str
    assert "idle" in repr_str
    assert "warning" in repr_str
