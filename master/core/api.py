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


class Meta(type):
    """
    Meta-class for dynamically managing and merging classes.
    """
    @staticmethod
    def attach_element(cls: Type[Any]):
        """
        Attaches a class to its corresponding meta_path registry.
        Args:
            cls (Type[Any]): The class to attach.
        Returns:
            Type[Any]: The processed class.
        """
        cls = call_classmethod(cls, '_attach_klass') or cls
        meta_path = getattr(cls, '__meta_path__', None)
        if meta_path:
            classes[meta_path].append(cls)
            _logger.debug(f"Attached class '{cls.__module__}.{cls.__name__}' to meta_path '{meta_path}'")
        return cls

    @staticmethod
    def create_merged_class(new_class_name: str, classes_list: List[Type[Any]], options: Optional[Dict[str, Any]] = None) -> Type[Any]:
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
        # Dynamically create the new class
        return type(new_class_name, tuple(classes_list), options)

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
        @wraps(func)
        def wrapper(*args, **kwargs):
            timer: Optional[threading.Timer] = getattr(wrapper, '_timer', None)
            if timer:
                # Cancel the previous timer if the function is called again
                timer.cancel()
            # Set a new timer to call the function after `wait` seconds
            timer = threading.Timer(wait, func, args=args, kwargs=kwargs)
            setattr(wrapper, '_timer', timer)
            timer.start()
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
        # Deduplicate classes to avoid MRO conflicts
        filtered_classes = Meta.deduplicate_classes(class_list)
        if not filtered_classes:
            continue
        # Generate the new class name and module path
        new_class_name = "_New" + meta_path.split(".")[-1]
        module_path = '.'.join(meta_path.split(".")[:-1])
        try:
            if len(filtered_classes) == 1:
                # If only one class remains after deduplication, directly assign it
                new_class = filtered_classes[0]
            else:
                # Create the new merged class
                new_class = Meta.create_merged_class(
                    new_class_name,
                    filtered_classes,
                    {'__module__': module_path, '__meta_path__': None}
                )
            # Dynamically assign the new class to the appropriate module
            module = sys.modules[module_path]
            setattr(module, meta_path.split(".")[-1], new_class)
            if len(filtered_classes) > 1:
                _logger.info(f"Assigned merged class '{new_class_name}' to '{meta_path}'")
        except KeyError:
            _logger.error(f"Module '{module_path}' not found for meta_path: {meta_path}")
        except TypeError as e:
            _logger.error(f"Failed to create merged class for meta_path '{meta_path}': {e}")
        except Exception as e:
            _logger.error(f"Unexpected error during class compilation for meta_path '{meta_path}': {e}", exc_info=True)
