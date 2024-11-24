from typing import Callable, Any


# noinspection PyPep8Naming
class lazy_property:
    """A decorator for lazy, cached properties."""
    def __init__(self, func):
        self.func = func
        self._name = func.__name__

    def __get__(self, instance, owner):
        if instance is None:
            return self
        if self._name not in instance.__dict__:
            instance.__dict__[self._name] = self.func(instance)
        return instance.__dict__[self._name]

    def __set__(self, instance, value):
        instance.__dict__[self._name] = value

    def __delete__(self, instance):
        if self._name in instance.__dict__:
            del instance.__dict__[self._name]


# noinspection PyPep8Naming
class classproperty:
    """
    A decorator for defining class-level properties.
    """
    __slots__ = 'func'

    def __init__(self, func: Callable):
        self.func = func

    def __get__(self, instance: Any, owner: Any):
        return self.func(owner)


# noinspection PyPep8Naming
class lazy_classproperty(classproperty):
    """A lazy, cached class-level property."""
    _registry = {}

    def __get__(self, instance: Any, owner: Any):
        if owner not in self._registry:
            self._registry[owner] = super().__get__(instance, owner)
        return self._registry[owner]

    def __set__(self, owner: Any, value: Any):
        self._registry[owner] = value

    def __delete__(self, owner: Any):
        if owner in self._registry:
            del self._registry[owner]
