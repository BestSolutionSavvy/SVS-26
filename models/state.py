from enum import Enum


class StateType(Enum):
    """Enumeration of state types."""
    IDLE = "idle"
    WARNING = "warning"
    VIOLATION = "violation"


class State:
    """Represents a state with type, id, and name."""
    
    def __init__(self, type: StateType, id: int, name: str):
        """
        Initialize a State.
        
        Args:
            type: The StateType of this state
            id: The unique identifier of this state
            name: The name of this state
        """
        self.type = type
        self.id = id
        self.name = name
    
    def __repr__(self) -> str:
        return f"State(type={self.type}, id={self.id}, name='{self.name}')"
