from __future__ import annotations

from models.rule import Rule
from models.state import State
from carla_bindings import LazyDict
from models.transition import Transition
from typing import Optional, Tuple
from datetime import datetime, timedelta


class StateMachine:
    """An implementation of a state machine that handles a traffic rule.
    
    Includes per-rule violation cool-down mechanism: once a VIOLATION state is reached,
    that specific rule cannot generate another violation notification for a cool-down period.
    Other rules are not affected.
    """

    def __init__(self, rule: Rule, violation_cooldown_seconds: float = 3.0):
        """
        Initialize a StateMachine with a given rule.

        Args:
            rule: The Rule that this state machine will check against
            violation_cooldown_seconds: Cool-down period after a violation for THIS rule only (default 3.0s)
        """
        self._rule = rule
        self._current_state = rule.initial_state
        self._violation_cooldown = timedelta(seconds=violation_cooldown_seconds)
        self._last_violation_time: Optional[datetime] = None

    def __repr__(self) -> str:
        return f"StateMachine(rule={self._rule.name}, current_state={self._current_state})"

    def is_violation_on_cooldown(self) -> bool:
        """Check if this SPECIFIC rule is currently in violation cool-down period."""
        if self._last_violation_time is None:
            return False
        return datetime.now() - self._last_violation_time < self._violation_cooldown

    def evaluate(self, data: LazyDict) -> Tuple[State, Optional[Transition]]:
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
        for transition in self._rule.transitions_from(self._current_state):
            if transition.verify(merged):
                self._current_state = transition.target
                last_transition = transition
                
                # Track violation timestamp for cool-down (ONLY for this rule)
                if self._current_state.type.name == 'VIOLATION':
                    self._last_violation_time = datetime.now()
                
                break
        return self._current_state, last_transition
