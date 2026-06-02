from __future__ import annotations

from models.rule import Rule
from models.state import State
from carla_bindings import LazyDict
from models.transition import Transition
from typing import Optional, Tuple


class StateMachine:
    """An implementation of a state machine that handles a traffic rule.
    """

    def __init__(self, rule: Rule):
        """
        Initialize a StateMachine with a given rule.

        Args:
            rule: The Rule that this state machine will check against
        """
        self._rule = rule
        self._current_state = rule.initial_state

    def __repr__(self) -> str:
        return f"StateMachine(rule={self._rule.name}, current_state={self._current_state})"
    
    @property
    def current_state(self) -> State:
        """Get the current state of the state machine."""
        return self._current_state
    
    @property
    def rule(self) -> Rule:
        """Get the rule associated with this state machine."""
        return self._rule

    def evaluate(self, data: LazyDict) -> Tuple[Optional[State], Optional[Transition]]:
        """
        Evaluate the current state based on the input data and update the state machine.

        Args:
            data: A dictionary of input data that may affect the state transitions
        Returns:
            A tuple of the new current state and the transition taken (if any)
        """
        
        merged_resolvers = {**self._rule.constants, **data._resolvers}
        merged = LazyDict(merged_resolvers)
        merged.update(data)
        
        last_transition = None
        current_state = None
        for transition in self._rule.transitions_from(self._current_state):
            if transition.verify(merged):
                self._current_state = transition.target
                current_state = transition.target
                last_transition = transition                
                break
        return current_state, last_transition
