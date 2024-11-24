from typing import Optional, Any, Type, List, Dict, Callable
from master.config.logging import get_logger
from master.core.structure import ModuleClassRegistry
from master.tools.misc import call_classmethod, is_class_norm_compliant
from functools import wraps
import threading

_logger = get_logger(__name__)


class ClassManager(type):
    """
    Manages dynamic class registration, merging, and deduplication.
    """
    _registry: Dict[str, ModuleClassRegistry] = {}

    @staticmethod
    def register_class(cls: Type[Any]):
        """
        Registers a class to the appropriate module path registry.
        """
        cls = call_classmethod(cls, '_attach_klass') or cls
        meta_path = getattr(cls, '__meta_path__', None)
        if meta_path:
            if meta_path not in ClassManager._registry:
                ClassManager._registry[meta_path] = ModuleClassRegistry()
            ClassManager._registry[meta_path].register_class(cls)
            _logger.debug(f'Registered class "{cls.__module__}.{cls.__name__}" under meta_path "{meta_path}"')
        return cls

    @staticmethod
    def create_merged_class(new_class_name: str, base_classes: List[Type[Any]], options: Optional[Dict[str, Any]] = None) -> Type[Any]:
        """
        Dynamically creates a new class by merging multiple base classes.
        """
        if not base_classes:
            raise ValueError('Base classes are required to create a merged class.')
        return type(new_class_name, tuple(base_classes), options or {})

    @staticmethod
    def filter_unique_classes(modules: List[str], registry: ModuleClassRegistry) -> List[Type[Any]]:
        """
        Filters and deduplicates classes, retaining only the most derived ones.
        """
        result, all_classes = [], []
        for module in reversed(modules):
            all_classes.extend(reversed(registry.module_classes[module]))
        all_classes += registry.core_classes
        for cls in all_classes:
            if not any(issubclass(other, cls) for other in all_classes if other != cls):
                result.append(cls)
        return result


class BaseClass:
    """
    A foundational base class that enforces norm compliance and registration.
    """
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not is_class_norm_compliant(cls.__name__):
            raise ValueError(f'Class "{cls.__module__}.{cls.__name__}" is not norm compliant')
        ClassManager.register_class(cls)


class ClassProperty:
    """
    A decorator for defining class-level properties.
    """
    def __init__(self, fget: Callable):
        self.fget = fget

    def __get__(self, instance, owner):
        return self.fget(owner)


def debounce(wait: float):
    """
    Decorator to debounce a function, delaying its execution.
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            timer: Optional[threading.Timer] = getattr(wrapper, '_timer', None)
            if timer:
                timer.cancel()
            timer = threading.Timer(wait, func, args=args, kwargs=kwargs)
            setattr(wrapper, '_timer', timer)
            timer.start()
        return wrapper
    return decorator


# noinspection PyProtectedMember
def compile_classes(modules: List[str]) -> Dict[str, Type[Any]]:
    """
    Compiles and merges classes for each meta_path in the registry.
    """
    from master.core.module.loader import reorder_module_names
    modules = reorder_module_names(modules)
    compiled_classes = {}
    for meta_path, registry in ClassManager._registry.items():
        if not registry:
            _logger.warning(f'No classes found for meta_path "{meta_path}"')
            continue
        filtered_classes = ClassManager.filter_unique_classes(modules, registry)
        if not filtered_classes:
            continue
        try:
            new_class_name = "_Merged" + meta_path.split(".")[-1]
            new_class = filtered_classes[0] if len(filtered_classes) == 1 else ClassManager.create_merged_class(new_class_name, filtered_classes)
            compiled_classes[meta_path] = new_class
        except Exception as e:
            _logger.error(f'Error compiling classes for meta_path "{meta_path}": {e}', exc_info=True)
    return compiled_classes
