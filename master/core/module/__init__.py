import sys
from pathlib import Path
from typing import Optional, Union, List, Iterable
from master import addons
from master.config import arguments
from master.config.logging import get_logger
from master.tools.collection import OrderedSet
from master.tools.enums import Enum
from master.core.db import PostgresManager
from master.data import git_repo_manager

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


from . import reader, tree, loader


def read_modules() -> tree.OrderedConfiguration:
    """
    Reads and processes module configurations, ensuring dependencies are ordered.
    Returns:
        OrderedConfiguration: An ordered configuration of modules.
    """
    current_configurations = reader.read_configurations()
    order_tree = tree.Tree(current_configurations[arguments['master_base_addon']])
    configurations_list = current_configurations.values()
    for configuration in configurations_list:
        order_tree.build_node(configuration)
    order_tree.build_links(configurations_list)
    incorrect, current_configurations = order_tree.order_nodes(current_configurations)
    if incorrect:
        _logger.warning(f'Missing dependencies {incorrect}.')
    return current_configurations


configurations: tree.OrderedConfiguration = {}


def main():
    """
    Main entry point for module loading and initialization.
    """
    if not arguments['pipeline']:
        git_repo_manager.setup()
    global configurations
    configurations = read_modules()
    if not configurations:
        _logger.error('No configurations found. Shutting down.')
        sys.exit(-1)
    for name in loader.default_modules(configurations.values()):
        loader.import_module(name, configurations)
