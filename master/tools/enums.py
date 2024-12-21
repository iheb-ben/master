import enum
from typing import Any, List, Optional


class Enum(enum.Enum):
    @classmethod
    def from_value(cls, value: Any, raise_error: bool = True) -> Optional['Enum']:
        """
        Returns the enum member corresponding to the given value.
        Args:
            value: The value to look up in the enum.
            raise_error: If True, raises an error when element is not found.
        Raises:
            ValueError: If no matching enum member is found.
        """
        for member in cls:
            if member.value == value:
                return member
        if not raise_error:
            return None
        raise ValueError(f'{value} is not a valid value for {cls.__name__}')

    @classmethod
    def names(cls) -> List[str]:
        """Returns the list of all member names corresponding to this class."""
        return [member.name for member in cls]
