from typing import List
from .transition import Transition
from .state import State


class Rule:
    """Represents a road rule as a list of transitions between states."""

    def __init__(self, name: str, constants: dict, transitions: List[Transition]):
        """
        Initialize a Rule.

        Parameters
        -------
        name: str
            The name of this rule
        constants: dict
            The list of constants for this rule
        transitions: List[Transition]
            The list of transitions for this rule
        """
        self.name = name
        self._transitions = transitions
        self._constants = constants

    def __repr__(self) -> str:
        return f"Rule(name='{self.name}', constants={self._constants})"

    @property
    def initial_state(self) -> State:
        """Get the initial state of this rule."""
        if not self._transitions:
            raise RuntimeError(
                "Rule has no transitions, initial_state is undefined")
        return self._transitions[0].source

    @property
    def constants(self) -> dict:
        """Get the constants for this rule."""
        return self._constants

    def transitions_from(self, state: State) -> List[Transition]:
        """Get all transitions originating from a given state."""
        return [t for t in self._transitions if t.source == state]
