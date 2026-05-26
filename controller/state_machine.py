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
        data = {**self._rule.constants, **data}
        for transition in self._rule.transitions_from(self._current_state):
            if transition.verify(data):
                self._current_state = transition.target
                break
        return self._current_state
        
