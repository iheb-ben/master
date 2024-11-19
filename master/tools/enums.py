import enum
from typing import Any, List


class Enum(enum.Enum):
    @classmethod
    def from_value(cls, value: Any) -> 'Enum':
        """
        Returns the enum member corresponding to the given value.
        Args:
            value: The value to look up in the enum.
        Raises:
            ValueError: If no matching enum member is found.
        """
        for member in cls:
            if member.value == value:
                return member
        raise ValueError(f'{value} is not a valid value for {cls.__name__}')

    @classmethod
    def names(cls) -> List[str]:
        """Returns the list of all member names corresponding to this class."""
        return [member.name for member in cls]
