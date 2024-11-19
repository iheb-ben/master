from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Optional, Any, Type, List, Dict
from master.config.logging import get_logger
from master.tools.misc import call_classmethod
from functools import wraps
import threading

_logger = get_logger(__name__)
classes: Dict[str, List[Type[Any]]] = defaultdict(list)


class AbstractMeta(ABC):
    @classmethod
    @abstractmethod
    def attach_element(cls, *args, **kwargs):
        pass


class Meta(AbstractMeta, type):
    def __new__(cls, *args, **kwargs):
        return cls.attach_element(type(*args, **kwargs))

    @classmethod
    def attach_element(cls, klass: Type[Any]):
        meta_path = getattr(klass, '__meta_path__', None)
        if meta_path:
            classes[meta_path].append(klass)
        return call_classmethod(klass, '_attach_klass') or klass

    @classmethod
    def create_merged_class(cls, new_class_name: str, classes_list: List[Type[Any]]) -> Type[Any]:
        """
        Dynamically creates a new class that merges multiple classes.
        The new class respects the Method Resolution Order (MRO) for super() calls.
        :param new_class_name: New merged class name.
        :param classes_list: List of classes to merge.
        :return: A new class with combined functionality.
        """
        if not classes_list:
            raise ValueError('classes_list must contain at least one class to merge.')

        # Check for a common base class
        root_base = classes_list[0].__bases__[0]
        if not all(root_base in cls.__mro__ for cls in classes_list):
            raise TypeError('All classes must share the same root base class.')

        new_class = type(new_class_name, tuple(classes_list), {})
        _logger.debug(f"Created merged class '{new_class_name}' with bases: {[cls.__name__ for cls in classes_list]}")
        return new_class


class ClassProperty:
    """ClassProperty decorator to allow properties at the class level."""
    def __init__(self, fget):
        self.fget = fget

    def __get__(self, instance, owner):
        return self.fget(owner)


def debounce(wait):
    """
    Decorator that debounces a function, postponing its execution until after `wait` seconds have elapsed since the last time it was called.
    :param wait: Time to wait before allowing the function to execute again.
    """
    def decorator(func):
        # noinspection PyProtectedMember
        @wraps(func)
        def wrapper(*args, **kwargs):
            if hasattr(wrapper, '_timer'):
                # Cancel the previous timer if the function is called again
                wrapper._timer.cancel()
            # Set a new timer to call the function after `wait` seconds
            wrapper._timer = threading.Timer(wait, func, args=args, kwargs=kwargs)
            wrapper._timer.start()
        return wrapper
    return decorator
