from transition import Transition
from state import State


class Rule:
    """Represents a road rule as a list of transitions between states."""

    def __init__(self, name: str, transitions: list[Transition]):
        """
        Initialize a Rule.
        
        Args:
            name: The name of this rule
            transitions: The list of transitions for this rule
        """
        self.name = name
        self._transitions = transitions
        
    def __repr__(self) -> str:
        return f"Rule(name='{self.name}')"
    
    @property
    def initial_state(self) -> State:
        """Get the initial state of this rule."""
        return self._transitions[0].source
    
    def transitions_from(self, state: State) -> list[Transition]:
        """Get all transitions originating from a given state."""
        return [t for t in self._transitions if t.source == state]