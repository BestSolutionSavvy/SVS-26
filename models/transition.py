from carla_bindings import LazyDict

from .state import State


class Transition:
    """Represents a transition between two states with a condition."""

    def __init__(self, condition: str, source: State, target: State):
        """
        Initialize a Transition.

        Parameters
        -------
        condition: str
            The condition string for this transition (private)
        source: State
            The source State
        target: State
            The target State
        """
        self._condition = condition
        self.source = source
        self.target = target

    @property
    def condition(self) -> str:
        """Get the condition string for this transition."""
        return self._condition

    def verify(self, data: LazyDict) -> bool:
        """
        Verify if the transition can occur based on the provided data.

        Parameters
        -------
        data: LazyDict
            Dictionary containing data to verify against

        Returns
        -------
        bool
            True if verification passes, False otherwise
        """
        return eval(self._condition, {}, data)

    def __repr__(self) -> str:
        return f"Transition({self.source.name} ---({self._condition})--> {self.target.name})"
