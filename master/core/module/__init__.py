import sys
from pathlib import Path
from typing import Optional, Union, List, Iterable
from master.config.parser import arguments
from master.config.logging import get_logger
from master.tools.collection import OrderedSet

_logger = get_logger(__name__)


# noinspection GrazieInspection
class Configuration:
    """
    Represents a module configuration.
    Attributes:
        name (str): The module name.
        location (Path): The path to the module.
        depends (List[str]): List of module dependencies.
        sequence (int): Load sequence of the module.
    """
    __slots__ = ('name', 'location', 'depends', 'sequence')

    def __init__(
        self,
        path: Path,
        depends: Optional[Union[List[str], str]] = None,
        sequence: Optional[int] = None
    ):
        """
        Initializes a Configuration instance.
        Args:
            path (Path): The path to the module.
            depends (Optional[Union[List[str], str]]): Module dependencies, can be a list or a single string.
            sequence (Optional[int]): The load sequence for the module.
        """
        self.name = str(path.name)
        self.location = path.parent
        base_addon = arguments.configuration['master_base_addon']
        # Normalize dependencies to a list of non-empty strings
        if depends is None:
            depends = []
        elif isinstance(depends, str):
            depends = [depends]
        if not isinstance(depends, Iterable) or isinstance(depends, bytes):
            raise ValueError(f'Addon "{self.name}" issue: Dependency format is incorrect in path "{path}".')
        self.depends = [name.strip() for name in depends if name]
        # Determine sequence with fallback logic
        if sequence is None or sequence <= 0:
            sequence = 16
            _logger.warning(f'Addon "{self.name}" issue: Incorrect or missing addon sequence, set to default 16.')
        self.sequence = sequence
        # Ensure master_base_addon is included as the first dependency
        if base_addon and self.name != base_addon and base_addon not in self.depends:
            self.depends.insert(0, base_addon)

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


from . import reader
from . import tree


def read_modules(shutdown: bool = False) -> Iterable[Configuration]:
    configurations = reader.read_configurations()
    if not configurations and shutdown:
        _logger.error('No configurations found. Shutting down.')
        sys.exit(-1)
    order_tree = tree.Tree(configurations[arguments.configuration['master_base_addon']])
    ordered_configurations = configurations.values()
    for configuration in ordered_configurations:
        order_tree.build_node(configuration)
    order_tree.build_links(ordered_configurations)
    incorrect, ordered_configurations = order_tree.order_nodes(configurations)
    if incorrect:
        _logger.warning(f'Missing dependencies {incorrect}.')
    return ordered_configurations
