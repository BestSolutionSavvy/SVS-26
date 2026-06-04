"""Tests for StateMachine and state transition logic."""
from controller.state_machine import StateMachine
from models.state import State
from carla_bindings import LazyDict


def test_state_machine_initial_state(dummy_rule, idle_state):
    """StateMachine initializes with rule's initial state."""
    sm = StateMachine(dummy_rule)
    assert sm._current_state == idle_state, "StateMachine should start in idle state"
    assert dummy_rule.initial_state == idle_state


def test_state_machine_transition_on_true_condition(dummy_rule, idle_state, warning_state):
    """StateMachine transitions when condition evaluates to True."""
    sm = StateMachine(dummy_rule)
    new_state, transition = sm.evaluate(LazyDict({"value": 11}))
    assert (
        new_state == warning_state
    ), f"Expected to transition to warning_state, got {new_state}"
    assert sm._current_state == warning_state
    assert transition is not None, "Transition should have been executed"


def test_state_machine_transition_back_on_false_condition(dummy_rule, idle_state, warning_state):
    """StateMachine transitions back when condition changes."""
    sm = StateMachine(dummy_rule)
    sm.evaluate(LazyDict({"value": 11}))  # go to warning
    new_state, transition = sm.evaluate(LazyDict({"value": 9}))  # go back to idle
    assert new_state == idle_state, "Should transition back to idle"
    assert sm._current_state == idle_state
    assert transition is not None, "Transition should have been executed"


def test_state_machine_stays_in_state_on_no_match(dummy_rule, idle_state):
    """StateMachine returns None when no transition matches."""
    sm = StateMachine(dummy_rule)
    # idle -> warning requires value > 10, but we have value = 10 so no match
    new_state, transition = sm.evaluate(LazyDict({"value": 10}))
    assert new_state is None, "Should return None when no transition matches"
    assert transition is None, "No transition should have been executed"
    assert sm.current_state == idle_state, "Internal state should remain in idle"


def test_state_machine_repr(dummy_rule):
    """StateMachine has readable repr."""
    sm = StateMachine(dummy_rule)
    repr_str = repr(sm)
    assert "StateMachine" in repr_str
    assert "Test Rule" in repr_str
