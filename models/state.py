from enum import Enum


class StateType(Enum):
    """Enumeration of state types."""
    IDLE = "idle"
    WARNING = "warning"
    VIOLATION = "violation"


class State:
    """Represents a state with type, id, and name."""
    
    def __init__(self, name: str):
        """
        Initialize a State.
        
        Args:
            name: The name of this state
        """
        self.type = StateType._member_map_.get(name.upper(), StateType.IDLE)  # Default to IDLE if not found
        self.id = id(self) 
        self.name = name
    
    def __repr__(self) -> str:
        return f"State(type={self.type}, id={self.id}, name='{self.name}')"