from typing import Callable
from state import State


class Transition:
    """Represents a transition between two states with a condition."""
    
    def __init__(self, condition: str, source: State, target: State, verify: Callable[[dict], bool]):
        """
        Initialize a Transition.
        
        Args:
            condition: The condition string for this transition (private)
            source: The source State
            target: The target State
            verify: A callable that verifies the transition with data
        """
        self._condition = condition
        self.source = source
        self.target = target
        self._verify = verify
    
    @property
    def condition(self) -> str:
        """Get the condition (read-only)."""
        return self._condition
    
    def verify(self, data: dict) -> bool:
        """
        Verify if the transition can occur based on the provided data.
        
        Args:
            data: Dictionary containing data to verify against
            
        Returns:
            True if verification passes, False otherwise
        """
        return self._verify(data)
    
    def __repr__(self) -> str:
        return f"Transition(condition='{self._condition}', source={self.source.name}, target={self.target.name})"
