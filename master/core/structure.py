from collections import defaultdict, OrderedDict
from pathlib import Path
from typing import Type, Any, List, Optional, Union, Set
from master.config.logging import get_logger
from master.tools.enums import Enum

_logger = get_logger(__name__)


class ConfigurationMode(Enum):
    BOTH = 'both'
    PIPELINE = 'pipeline'
    INSTANCE = 'instance'


# noinspection GrazieInspection
class Configuration:
    """
    Represents a module configuration.
    Attributes:
        name (str): The module name.
        location (Path): The path to the module.
        depends (List[str]): List of module dependencies.
        reversed_depends (List[str]): List of parent module dependencies.
        sequence (int): Load sequence of the module.
        auto_install (bool): Default state of the module.
        mode (ConfigurationMode): Module mode.
        kwargs (Dict[str, Any]): Unsupported arguments
    """
    __slots__ = ('name', 'location', 'reversed_depends', 'depends', 'sequence', 'auto_install', 'mode', 'kwargs')

    def __init__(
        self,
        path: Path,
        depends: Optional[Union[List[str], str]] = None,
        sequence: Optional[int] = None,
        auto_install: bool = False,
        mode: Optional[Union[str, ConfigurationMode]] = None,
        **kwargs
    ):
        """
        Initializes a Configuration instance.
        Args:
            path (Path): The path to the module.
            depends (Optional[Union[List[str], str]]): Module dependencies, can be a list or a single string.
            sequence (Optional[int]): The load sequence for the module.
            auto_install (bool): The default state of the module.
            mode (str): The module mode.
        """
        self.name = str(path.name)
        self.location = path.parent
        self.auto_install = auto_install
        if not mode:
            mode = ConfigurationMode.INSTANCE
        elif isinstance(mode, str):
            mode = ConfigurationMode.from_value(mode.lower())
        elif not isinstance(mode, ConfigurationMode):
            raise ValueError(f'Addon "{self.name}" issue: Incorrect mode value {mode}.')
        self.mode = mode
        base_addon = arguments['master_base_addon']
        # Normalize dependencies to a list of non-empty strings
        if depends is None:
            depends = []
        elif isinstance(depends, str):
            depends = [depends]
        if not isinstance(depends, Iterable):
            raise ValueError(f'Addon "{self.name}" issue: Dependency format is incorrect in path "{path}".')
        self.depends = [name.strip() for name in depends if name]
        self.reversed_depends = []
        # Determine sequence with fallback logic
        if sequence is None or sequence <= 0:
            sequence = 16
            _logger.debug(f'Addon "{self.name}": set sequence to default 16.')
        self.sequence = sequence
        # Ensure master_base_addon is included as the first dependency
        if base_addon and self.name != base_addon and base_addon not in self.depends:
            self.depends.insert(0, base_addon)
        if base_addon and self.name == base_addon:
            self.depends = []
        self.kwargs = kwargs
        if kwargs:
            _logger.warning(f'Addon "{self.name}" unsupported parameters: {list(kwargs.keys())}')

    @property
    def path(self) -> Path:
        """
        Extracts the module path from its name and location.
        Returns:
            str: The full path of the module.
        """
        return self.location / self.name

    def __repr__(self) -> str:
        """Returns a string representation of the Configuration instance."""
        return f'Configuration({self.name})'


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
        If the module starts with 'master.addons.', the third part is used; otherwise, returns '_'.
        """
        if cls.__module__.startswith('master.addons.'):
            return cls.__module__.split('.')[2]
        return '_'


class ModuleManager(OrderedDict):
    def __init__(self):
        super().__init__()
        self.order: List[str] = list()
        self.installed: Set[str] = set()
        self.pending: Set[str] = set()

    def add(self, configuration: Configuration):
        self[configuration.name] = configuration

    def select(self, names: List[str]) -> Dict[str, Configuration]:
        selected_modules = OrderedDict()
        if names:
            for key, item in self.items():
                if key not in names:
                    continue
                selected_modules[key] = item
        return selected_modules
