from threading import RLock
from typing import Dict, Any


# noinspection PyPep8Naming
class class_property:
    def __init__(self, fget=None, fset=None, fdel=None, doc=None):
        self.fget = fget
        self.fset = fset
        self.fdel = fdel
        self.__doc__ = doc or (fget.__doc__ if fget else None)

    def __get__(self, instance, owner):
        if self.fget is None:
            raise AttributeError('unreadable attribute')
        return self.fget(owner)

    def __set__(self, owner, value):
        if self.fset is None:
            raise AttributeError("can't set attribute")
        self.fset(owner, value)

    def __delete__(self, owner):
        if self.fdel is None:
            raise AttributeError("can't delete attribute")
        self.fdel(owner)

    def getter(self, func):
        return type(self)(func, self.fset, self.fdel, func.__doc__)

    def setter(self, func):
        return type(self)(self.fget, func, self.fdel, self.__doc__)

    def deleter(self, func):
        return type(self)(self.fget, self.fset, func, self.__doc__)


# noinspection PyPep8Naming
class lazy_property(property):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attr_name = f'_{self.fget.__name__}'

    # noinspection PyMethodOverriding
    def __get__(self, instance, owner):
        if instance is None:
            return self
        if not hasattr(instance, self.attr_name):
            setattr(instance, self.attr_name, super().__get__(instance, owner))
        return getattr(instance, self.attr_name)


# noinspection PyPep8Naming
class lazy_class_property(class_property):
    DATA: Dict[str, Any] = {}
    _lock = RLock()

    def _attribute_name(self, owner):
        return f'{owner.__module__}.{owner.__qualname__}.{self.fget.__name__}'

    def __get__(self, instance, owner):
        attr_name = self._attribute_name(owner)
        with self._lock:
            if attr_name not in self.DATA:
                self.DATA[attr_name] = super().__get__(instance, owner)
            return self.DATA[attr_name]

    def __set__(self, owner, value):
        attr_name = self._attribute_name(owner)
        with self._lock:
            self.DATA[attr_name] = value

    def __delete__(self, owner):
        attr_name = self._attribute_name(owner)
        with self._lock:
            if attr_name in self.DATA:
                del self.DATA[attr_name]
