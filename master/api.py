from typing import Callable, Any, Type, Dict, Optional
import threading


# noinspection PyPep8Naming
class lazy_property:
    """A decorator for lazy, cached properties."""
    __slots__ = ('__func__', '_name')

    def __init__(self, func: Callable):
        self.__func__ = func
        self._name = func.__name__

    def __get__(self, instance: Optional[object], owner: Type[object]) -> Any:
        if instance is None:
            return self
        if self._name not in instance.__dict__:
            instance.__dict__[self._name] = self.__func__(instance)
        return instance.__dict__[self._name]

    def __set__(self, instance: object, value: Any) -> None:
        instance.__dict__[self._name] = value

    def __delete__(self, instance: object) -> None:
        if self._name in instance.__dict__:
            del instance.__dict__[self._name]


# noinspection PyPep8Naming
class classproperty:
    """
    A decorator for defining class-level properties.
    """
    __slots__ = '__func__'

    def __init__(self, func: Callable):
        self.__func__ = func

    def __get__(self, instance: Optional[object], owner: Type[object]) -> Any:
        return self.__func__(owner)


# noinspection PyPep8Naming
class lazy_classproperty(classproperty):
    """A lazy, cached class-level property."""
    __slots__ = ('__func__', '_name')
    _register: Dict[str, Any] = {}
    _lock = threading.Lock()

    def __init__(self, func: Callable):
        super().__init__(func)
        self._name = func.__name__

    def __read_name(self, owner: Type[object]):
        return f'{owner.__module__}.{owner.__name__}.{self._name}'

    def __get__(self, instance: Optional[object], owner: Type[object]) -> Any:
        func_name = self.__read_name(owner)
        with self._lock:
            if func_name not in self.__class__._register:
                self.__class__._register[func_name] = super().__get__(instance, owner)
            return self.__class__._register[func_name]

    def __set__(self, instance: object, value: Any) -> None:
        func_name = self.__read_name(instance.__class__)
        with self._lock:
            self.__class__._register[func_name] = value
