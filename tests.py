from controller.state_machine import StateMachine
from models.transition import Transition
from models.state import State
from models.rule import Rule
from carla_bindings import LazyDict
from utils.parsing_utils import parse_rule_file


def test_state_machine_transitions():
    idle_state = State("idle")
    warning_state = State("warning")
    dummy_rule = Rule(
        name="Dummy Rule",
        constants={"threshold": 10},
        transitions=[
            Transition(condition="value > threshold",
                       source=idle_state, target=warning_state),
            Transition(condition="value <= threshold",
                       source=warning_state, target=idle_state),
        ]
    )
    sm = StateMachine(dummy_rule)

    assert dummy_rule.initial_state == idle_state
    assert sm._current_state == idle_state

    state_after_warning = sm.evaluate(LazyDict({'value': 11}))
    assert state_after_warning == warning_state
    assert sm._current_state == warning_state

    state_after_idle = sm.evaluate(LazyDict({'value': 9}))
    assert state_after_idle == idle_state
    assert sm._current_state == idle_state


def test_transition_verify():
    idle_state = State("idle")
    warning_state = State("warning")
    t = Transition(condition="x == 5", source=idle_state, target=warning_state)
    assert t.verify(LazyDict({'x': 5})) is True
    assert t.verify(LazyDict({'x': 4})) is False


def test_rule_parsing():
    rule = parse_rule_file('./admin/rules/lane_keeping.yaml')
    assert rule is not None
    assert rule.name == 'lane_keeping'
    
    assert 'warning_threshold' in rule.constants
    assert rule.constants['warning_threshold'] == 0.4

    assert len(rule._transitions) == 10

    assert any(t.target.name == 'violation' for t in rule._transitions)
