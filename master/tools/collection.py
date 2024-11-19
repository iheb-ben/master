from collections import OrderedDict
from collections.abc import Iterable
from typing import Optional, Any, Iterator


def is_complex_iterable(obj: Any) -> bool:
    """Check if the object is iterable but exclude strings and basic numbers (int, float)."""
    return isinstance(obj, Iterable) and not isinstance(obj, (str, int, float))


class OrderedSet(Iterable):
    """
    A set that preserves the insertion order of elements.
    Attributes:
        _data (OrderedDict): An ordered dictionary to store the elements as keys.
    """
    __slots__ = '_data'

    def __init__(self, iterable: Optional[Any] = None):
        """Initializes an OrderedSet, optionally with elements from an iterable."""
        self._data = OrderedDict()
        if iterable:
            self.update(is_complex_iterable(iterable) and iterable or [iterable])

    def add(self, value: Any) -> None:
        """Adds an element to the set, maintaining order and uniqueness."""
        self._data[value] = None

    def update(self, iterable: Any) -> None:
        """Adds multiple elements from an iterable to the set."""
        if not is_complex_iterable(iterable):
            raise TypeError("Provided value must be a complex iterable.")
        for value in iterable:
            self.add(value)

    def copy(self) -> 'OrderedSet':
        """Returns a shallow copy of the OrderedSet."""
        return self.__class__(self._data.keys())

    def index(self, item: Any) -> int:
        """
        Returns the index of the specified item in the set.
        Args:
            item (Any): The item to find the index for.
        Returns:
            int: The index of the item, or -1 if not found.
        """
        for index, current in enumerate(self._data.keys()):
            if current == item:
                return index
        return -1

    def remove(self, item: Any) -> None:
        """
        Removes the specified item from the set.
        Args:
            item (Any): The item to remove.
        Raises:
            KeyError: If the item is not in the set.
        """
        del self._data[item]

    def __getitem__(self, index: int) -> Any:
        """
        Gets the element at the specified index.
        Args:
            index (int): The index of the element.
        Returns:
            Any: The element at the given index.
        """
        return list(self._data.keys())[index]

    def __add__(self, other: 'OrderedSet') -> 'OrderedSet':
        """
        Returns a new OrderedSet containing elements of this set followed by elements of another set.
        Args:
            other (OrderedSet): Another OrderedSet to add.
        Returns:
            OrderedSet: A new OrderedSet with combined elements.
        """
        if not isinstance(other, OrderedSet):
            raise TypeError(f'Can only add another {self.__class__.__name__}')
        return self.__class__(list(self._data.keys()) + list(other._data.keys()))

    def __sub__(self, other: 'OrderedSet') -> 'OrderedSet':
        """Returns a new OrderedSet with elements that are in this set but not in the other."""
        if not isinstance(other, OrderedSet):
            raise TypeError(f'Can only subtract another {self.__class__.__name__}')
        return self.__class__([value for value in self if value not in other])

    def __contains__(self, value: Any) -> bool:
        """Checks if the value is in the set."""
        return value in self._data

    def __iter__(self) -> Iterator[Any]:
        """Returns an iterator over the set elements."""
        return iter(self._data.keys())

    def __reversed__(self) -> Iterator[Any]:
        """Returns a reverse iterator over the set elements."""
        return reversed(self._data.keys())

    def __repr__(self) -> str:
        """Returns a string representation of the custom set."""
        return f"{self.__class__.__name__}({list(self._data.keys())})"

    def __len__(self) -> int:
        """Returns the number of elements in the set."""
        return len(self._data)

    def __eq__(self, other: Any) -> bool:
        """Checks if this OrderedSet is equal to another OrderedSet, list, or set."""
        if isinstance(other, OrderedSet):
            return list(self._data.keys()) == list(other._data.keys())
        elif isinstance(other, list):
            return list(self._data.keys()) == other
        elif isinstance(other, set):
            return set(self._data.keys()) == other
        return False

    def __hash__(self) -> int:
        """Returns a hash based on the set's elements."""
        return hash(tuple(self._data.keys()))


class LastIndexOrderedSet(OrderedSet):
    """
    A subclass of OrderedSet that updates the position of an element to the end
    whenever it's added, effectively maintaining the most recent insertion order.
    """

    def add(self, value: Any) -> None:
        """Adds an element to the set, moving it to the end if it already exists."""
        if value in self._data:
            self.remove(value)  # Remove the value if it already exists.
        super().add(value)  # Add it again, moving it to the end.
