import logging
from collections import defaultdict
from typing import Type, Any, Dict, List, Optional
from master.api import lazy_classproperty
from master.tools.methods import call_classmethod
from master.tools.norms import is_class_norm_compliant

_logger = logging.getLogger(__name__)


class ModuleClassRegistry:
    """
    Manages the registry of classes, organizing them by their associated module.
    """
    __slots__ = ('module_classes', 'core_classes')

    def __init__(self):
        self.module_classes = defaultdict(list)  # Classes grouped by module
        self.core_classes = []  # Core classes not associated with specific modules

    def register_class(self, cls: Type[Any]):
        """
        Registers a class, grouping it by its module or marking it as core.
        """
        module_name = self._extract_module_name(cls)
        if module_name == '_':
            self.core_classes.append(cls)
        else:
            self.module_classes[module_name].append(cls)

    @staticmethod
    def _extract_module_name(cls: Type[Any]) -> str:
        """
        Extracts the module name for a given class.
        If the module starts with 'master.addons.', the addon name part is used; otherwise, returns '_'.
        """
        if cls.__module__.startswith('master.addons.'):
            return cls.__module__.split('.')[2]
        return '_'


class ClassManager:
    """
    Manages dynamic class registration, merging, and deduplication.
    """
    __slots__ = '_classes'
    _registry: Dict[str, ModuleClassRegistry] = {}

    def __init__(self, modules: List[str]):
        """
        Compiles and merges classes for each meta_path in the registry.
        """
        self._classes: Dict[str, Type[Any]] = {}
        for meta, registry in self._registry.items():
            if not registry:
                _logger.warning(f'No classes found for meta_path "{meta}"')
                continue
            filtered_classes = self.filter_unique_classes(modules, registry)
            if not filtered_classes:
                continue
            try:
                self._classes[meta] = (filtered_classes[0] if len(filtered_classes) == 1 else
                                       self.create_merged_class("_Merged" + meta.split(".")[-1], filtered_classes))
            except Exception as e:
                _logger.error(f'Error compiling classes for meta_path "{meta}": {e}', exc_info=True)

    def __getitem__(self, item) -> Type[Any]:
        return self._classes[item]

    def __getattribute__(self, item):
        try:
            attribute = super().__getattribute__(item)
        except AttributeError:
            if hasattr(self, '_classes'):
                for key in self._classes:
                    if key.endswith(item):
                        return self[key]
            raise

    @staticmethod
    def register_class(cls: Type['BaseClass']):
        """
        Registers a class to the appropriate module path registry.
        """
        call_classmethod(cls, '_before_register')
        if cls.__meta__:
            if cls.__meta__ not in ClassManager._registry:
                ClassManager._registry[cls.__meta__] = ModuleClassRegistry()
            ClassManager._registry[cls.__meta__].register_class(cls)
            _logger.debug(f'Registered class "{cls.__module__}.{cls.__name__}" under meta_path "{cls.__meta__}"')
            call_classmethod(cls, '_after_register')
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
        for module in modules:
            all_classes.extend(reversed(registry.module_classes[module]))
        all_classes += registry.core_classes
        for cls in all_classes:
            if not any(issubclass(other, cls) for other in all_classes if other != cls):
                result.append(cls)
        return result


class BaseClass(object):
    """
    A foundational base class that enforces norm compliance and registration.
    """
    def __init_subclass__(cls, *args, **kwargs):
        super().__init_subclass__(*args, **kwargs)
        if not is_class_norm_compliant(cls.__name__):
            raise ValueError(f'Class "{cls.__module__}.{cls.__name__}" is not norm compliant')
        ClassManager.register_class(cls)

    # noinspection PyMethodParameters
    @lazy_classproperty
    def __meta__(cls) -> Optional[str]:
        index = list(cls.__mro__).index(BaseClass) - 1
        if index < 0:
            return None
        mro = cls.__mro__[index]
        return f'{mro.__module__}.{mro.__name__}'
