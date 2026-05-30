from carla_bindings import LazyDict

from .state import State


class Transition:
    """Represents a transition between two states with a condition."""
    
    def __init__(self, condition: str, source: State, target: State):
        """
        Initialize a Transition.
        
        Args:
            condition: The condition string for this transition (private)
            source: The source State
            target: The target State
        """
        self._condition = condition
        self.source = source
        self.target = target
    
    @property
    def condition(self) -> str:
        """Get the condition (read-only)."""
        return self._condition
    
    def verify(self, data: LazyDict) -> bool:
        """
        Verify if the transition can occur based on the provided data.
        
        Args:
            data: Dictionary containing data to verify against
            
        Returns:
            True if verification passes, False otherwise
        """
        return eval(self._condition, {}, data)

    def __repr__(self) -> str:
        return f"Transition(condition='{self._condition}', source={self.source.name}, target={self.target.name})"


if __name__ == "__main__":
    idle_state = State("idle")
    warning_state = State("warning")
    
    transition = Transition("speed > 100", idle_state, warning_state)
    
    print(transition)
    print(transition.verify(LazyDict({'speed': 120})))  # Should return True
    print(transition.verify(LazyDict({'speed': 80})))   # Should return False 