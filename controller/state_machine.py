from models.rule import Rule
from models.state import State


class StateMachine:
    """An implementation of a state machine that handles a traffic rule."""

    def __init__(self, rule: Rule):
        """
        Initialize a StateMachine with a given rule.

        Args:
            rule: The Rule that this state machine will check against
        """
        self._rule = rule
        self._current_state = rule.initial_state

    def __repr__(self) -> str:
        return f"StateMachine(rule={self._rule}, current_state={self._current_state})"

    def evaluate(self, data: dict) -> State:
        """
        Evaluate the current state based on the input data and update the state machine.

        Args:
            data: A dictionary of input data that may affect the state transitions
        """
        # Preserve LazyDict if data is one by merging at the resolver level
        from carla_bindings import LazyDict
        
        if isinstance(data, LazyDict):
            # Create a new LazyDict with both constants and original resolvers
            merged_resolvers = {**self._rule.constants, **data._resolvers}
            merged = LazyDict(merged_resolvers)
            merged.update(data)  # Add already-computed values
        else:
            # Fallback for regular dicts
            merged = {**self._rule.constants, **data}
        
        for transition in self._rule.transitions_from(self._current_state):
            if transition.verify(merged):
                self._current_state = transition.target
                break
        return self._current_state


def test_sm():
    from models.transition import Transition
    warning_state = State("warning")
    idle_state = State("idle")
    dummy_rule = Rule(
        name="Dummy Rule",
        constants={"threshold": 10},
        transitions=[
            Transition(condition="value > threshold", source=idle_state, target=warning_state),
            Transition(condition="value <= threshold", source=warning_state, target=idle_state),
        ])
    sm = StateMachine(dummy_rule)
    print(sm)
    sm.evaluate({'value': 11})
    print(sm)
    sm.evaluate({'value': 9})
    print(sm)

    
