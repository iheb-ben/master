from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Optional, Any, Type, List, Dict, Callable
from master.config.logging import get_logger
from master.tools.misc import call_classmethod
from functools import wraps
import threading
import sys

_logger = get_logger(__name__)

# Global registry for classes
classes: Dict[str, List[Type[Any]]] = defaultdict(list)


class AbstractMeta(ABC):
    """
    Abstract base class defining the required method for metaclasses.
    """
    @classmethod
    @abstractmethod
    def attach_element(cls, *args, **kwargs):
        pass


class Meta(AbstractMeta, type):
    """
    Meta-class for dynamically managing and merging classes.
    """
    @classmethod
    def attach_element(cls, klass: Type[Any]):
        """
        Attaches a class to its corresponding meta_path registry.
        Args:
            klass (Type[Any]): The class to attach.
        Returns:
            Type[Any]: The processed class.
        """
        klass = call_classmethod(klass, '_attach_klass') or klass
        meta_path = getattr(klass, '__meta_path__', None)
        if meta_path:
            classes[meta_path].append(klass)
            _logger.debug(f"Attached class '{klass.__name__}' to meta_path '{meta_path}'")
        return klass

    @classmethod
    def create_merged_class(cls, new_class_name: str, classes_list: List[Type[Any]], options: Optional[Dict[str, Any]] = None) -> Type[Any]:
        """
        Dynamically creates a new class by merging multiple classes.
        Args:
            new_class_name (str): Name of the newly created class.
            classes_list (List[Type[Any]]): List of classes to merge.
            options (Optional[Dict[str, Any]]): Additional class options like attributes.
        Returns:
            Type[Any]: The newly created class.
        Raises:
            ValueError: If the `classes_list` is empty.
            TypeError: If the classes do not share a common base class.
        """
        options = options or {}
        if not classes_list:
            raise ValueError('classes_list must contain at least one class to merge.')
        # Validate that all classes share a common base class
        root_base = classes_list[0].__bases__[0]
        if not all(root_base in cls.__mro__ for cls in classes_list):
            raise TypeError('All classes must share the same root base class.')
        # Dynamically create the new class
        new_class = type(new_class_name, tuple(classes_list), options)
        _logger.debug(f"Created merged class '{new_class_name}' with bases: {[cls.__name__ for cls in classes_list]}")
        return new_class

    @classmethod
    def deduplicate_classes(cls, classes_list: List[Type[Any]]) -> List[Type[Any]]:
        """
        Removes redundant base classes, keeping only the most derived ones.
        Args:
            classes_list (List[Type[Any]]): List of classes to deduplicate.
        Returns:
            List[Type[Any]]: A filtered list of classes.
        """
        result = []
        for klass in reversed(classes_list):
            if not any(issubclass(other, klass) for other in classes_list if other != klass):
                result.append(klass)
        return result


class Class:
    """
    Base class for all managed classes. Automatically registers subclasses in `Meta`.
    """
    def __init_subclass__(cls, **kwargs):
        """
        Automatically called when a new subclass is created. Registers the class with `Meta`.
        """
        super().__init_subclass__(**kwargs)
        Meta.attach_element(cls)


class ClassProperty:
    """
    A decorator for creating class-level properties.
    """
    def __init__(self, fget: Callable):
        self.fget = fget

    def __get__(self, instance, owner):
        return self.fget(owner)


def debounce(wait: float):
    """
    Decorator that debounces a function, postponing its execution until after `wait` seconds.
    Args:
        wait (float): Time in seconds to wait before executing the function.
    Returns:
        Callable: The decorated function.
    """
    def decorator(func: Callable):
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


def compile_classes():
    """
    Dynamically creates and assigns new merged classes for each meta_path in `classes`.
    """
    for meta_path, class_list in classes.items():
        if not class_list:
            _logger.warning(f"No classes found for meta_path: {meta_path}")
            continue
        if len(class_list) == 1:
            continue
        # Deduplicate classes to avoid MRO conflicts
        filtered_classes = Meta.deduplicate_classes(class_list)
        # Generate the new class name and module path
        new_class_name = "Super" + meta_path.split(".")[-1]
        module_path = '.'.join(meta_path.split(".")[:-1])
        if len(filtered_classes) == 1:
            # Dynamically assign the new class to the appropriate module
            module = sys.modules[module_path]
            setattr(module, meta_path.split(".")[-1], filtered_classes[0])
        else:
            try:
                # Create the new class
                new_class = Meta.create_merged_class(
                    new_class_name,
                    filtered_classes,
                    {'__module__': module_path, '__meta_path__': None}
                )
                # Dynamically assign the new class to the appropriate module
                module = sys.modules[module_path]
                setattr(module, meta_path.split(".")[-1], new_class)
                _logger.info(f"Assigned merged class '{new_class_name}' to '{meta_path}'")
            except KeyError:
                _logger.error(f"Module '{module_path}' not found for meta_path: {meta_path}")
            except TypeError as e:
                _logger.error(f"Failed to create merged class for meta_path '{meta_path}': {e}")
            except Exception as e:
                _logger.error(f"Unexpected error during class compilation for meta_path '{meta_path}': {e}", exc_info=True)
