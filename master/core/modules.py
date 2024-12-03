import json
import logging
import sys
from collections import OrderedDict
from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path
from typing import Optional, Union, List, Iterable, Dict, Generator, Any, Tuple

from master import pip, addons
from master.core import arguments
from master.tools.collection import LastIndexOrderedSet
from master.tools.enums import Enum
from master.tools.norms import is_module_norm_compliant

_logger = logging.getLogger(__name__)
base_addon = 'base'


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
        if self.name != base_addon and base_addon not in self.depends:
            self.depends.insert(0, base_addon)
        if self.name == base_addon:
            self.depends = []
        self.kwargs = kwargs

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


configurations: Dict[str, Configuration] = OrderedDict()


def iterate_addons_paths() -> Generator[Path, None, None]:
    """
    Iterates through all addon paths specified in the configuration.
    Yields:
        Path: A valid addons directory path.
    """
    base_path = Path('./master/addons').absolute().resolve()
    current_paths = [str(Path(p).absolute().resolve()) for p in arguments['addons_paths']]
    if str(base_path) not in current_paths and base_path.is_dir():
        current_paths.insert(0, str(base_path))
    elements_found = False
    for path in LastIndexOrderedSet(current_paths):
        addons_path = Path(path)
        if addons_path.is_dir():
            elements_found = True
            yield addons_path
        else:
            _logger.warning(f'Invalid addons path: "{addons_path.absolute().resolve()}"')
    if not elements_found:
        _logger.error('No valid addons paths were found.')


def read_module_configuration(module_path: Path) -> Optional[Dict[str, Any]]:
    """
    Reads the configuration for a module from its configuration.json.
    Args:
        module_path (Path): Path to the module directory.
    Returns:
        Optional[Dict[str, Any]]: Parsed configuration dictionary, or None if invalid.
    """
    if not module_path.is_dir():
        return None
    config_file = module_path / 'configuration.json'
    if not config_file.is_file():
        return None
    try:
        with config_file.open('r') as file:
            configuration = json.load(file)
        if module_path.joinpath('__init__.py').exists():
            return configuration
    except (OSError, json.JSONDecodeError) as e:
        _logger.error(f'Failed to load configuration for {module_path.name}: {e}')
    return None


class Node:
    """
    Represents a single node in the dependency tree.
    Attributes:
        name (str): The name of the module.
        sequence (int): The load sequence of the module.
        factor (int): The factor of the module.
        children (List[Node]): List of child nodes (dependencies of this node).
        parents (List[Node]): List of parent nodes (nodes that depend on this node).
    """
    __slots__ = ('name', 'sequence', 'factor', 'children', 'parents')

    def __init__(self, configuration: Configuration):
        self.name = configuration.name
        self.sequence = configuration.sequence
        self.factor = 10
        self.children: List[Node] = []
        self.parents: List[Node] = []

    def add_child(self, child_node: 'Node'):
        """
        Adds a child node (dependency) to this node.
        Args:
            child_node (Node): The child node to add.
        """
        self.children.append(child_node)
        child_node.parents.append(self)
        child_node.factor += self.factor

    def __repr__(self) -> str:
        """Returns a string representation of the Node instance."""
        return f'Node({self.name})'


class Graph:
    """
    Represents a dependency tree for managing module configurations.
    Attributes:
        _configurations (Dict[str, Configuration]): All configurations.
        _nodes (Dict[str, Node]): Mapping of module names to their corresponding Node objects.
        _incorrect (List[str]): List of missing dependencies that could not be resolved.
    """
    __slots__ = ('_configurations', '_nodes', '_incorrect')

    def __init__(self):
        self._configurations: Dict[str, Configuration] = {}
        for addons_path in iterate_addons_paths():
            is_empty = True
            for module_path in addons_path.iterdir():
                if module_path.is_file() or module_path.name.startswith('_'):
                    continue
                configuration_data = read_module_configuration(module_path)
                if configuration_data is not None:
                    if not is_module_norm_compliant(module_path.name):
                        raise ValueError(f'Module name "{module_path.name}" is not norm compliant')
                    configuration_data['path'] = module_path
                    self._configurations[module_path.name] = Configuration(**configuration_data)
                    is_empty = False
                else:
                    _logger.warning(f'Ignored invalid module: {module_path.name}')
            if is_empty:
                _logger.warning(f'No valid modules found in: {addons_path}')
            else:
                pip.install_requirements(addons_path / 'requirements.txt')
        base_configuration = self._configurations[base_addon]
        self._nodes: Dict[str, Node] = {base_configuration.name: Node(base_configuration)}
        self._incorrect: List[str] = []
        configurations_list = self._configurations.values()
        for configuration in configurations_list:
            self.build_node(configuration)
        self.build_links(configurations_list)

    def build_node(self, configuration: Configuration):
        """
        Builds a node for a given module configuration if it doesn't already exist.
        Args:
            configuration (Configuration): The module configuration to add.
        """
        if configuration.name not in self._nodes:
            self._nodes[configuration.name] = Node(configuration)

    def build_links(self, current_configurations: Iterable[Configuration]):
        """
        Establishes parent-child relationships based on module dependencies.
        Args:
            current_configurations (Iterable[Configuration]): A list of module configurations to process.
        """
        for configuration in current_configurations:
            for dependency in configuration.depends:
                if dependency not in self._nodes:
                    self._incorrect.append(dependency)
                    try:
                        configuration.depends.remove(dependency)
                    except ValueError:
                        continue
                else:
                    self._nodes[dependency].add_child(self._nodes[configuration.name])
        for node in self._nodes.values():
            if node.name == base_addon:
                continue
            for dependency in node.children:
                if node in self._collect_all_nodes(dependency):
                    raise ValueError(f'Circular dependency detected in addon "{node.name}": "{dependency.name}" is in the recursion stack.')

    @classmethod
    def _collect_all_nodes(cls, node: Node) -> List[Node]:
        """
        Collects all nodes reachable from a given node, avoiding duplicates.
        Args:
            node (Node): The starting node.
        Returns:
            List[Node]: A list of all reachable nodes.
        """
        visited = set()
        stack = [node]
        nodes = []
        while stack:
            current_node = stack.pop()
            if current_node.name not in visited:
                visited.add(current_node.name)
                nodes.append(current_node)
                stack.extend(current_node.children)
        return nodes

    @classmethod
    def _sort_all_nodes(cls, node: Node) -> Tuple[int, int, int, str]:
        """
        Sorting key for ordering nodes.
        Args:
            node (Node): The node to sort.
        Returns:
            Tuple[int, int, int, str]: A tuple used to sort nodes by the factor, sequence, number of parents, and name.
        """
        return node.factor, node.sequence, len(node.parents), node.name

    def order_configurations(self) -> Dict[str, Configuration]:
        """
        Orders nodes based on dependencies and sequence.
        """
        reversed_depends: Dict[str, List[str]] = {}
        ordered_names: List[str] = []
        ordered_configurations: Dict[str, Configuration] = OrderedDict()
        for node in sorted(self._collect_all_nodes(self._nodes[base_addon]), key=self._sort_all_nodes):
            ordered_configurations[node.name] = self._configurations[node.name]
            reversed_depends[node.name] = [child.name for child in node.children]
            ordered_names.append(node.name)
        for configuration in ordered_configurations.values():
            configuration.reversed_depends = reversed_depends[configuration.name]
            configuration.depends = [name for name in ordered_names if name in configuration.depends]
        if self._incorrect:
            _logger.warning(f'Missing dependencies {self._incorrect}.')
        return ordered_configurations

    def __repr__(self) -> str:
        """Returns a string representation of the Graph instance."""
        return f'Graph({len(self._nodes.keys())})'


def import_module(name: str):
    """
    Dynamically imports a module and its dependencies.
    Args:
        name (str): The name of the module to import.
    """
    if hasattr(addons, name):
        return
    # Import dependencies recursively
    for dependency in configurations[name].depends:
        import_module(dependency)
    try:
        module_path = configurations[name].path / '__init__.py'
        spec = spec_from_file_location(f"{addons.__name__}.{name}", module_path)
        # Ensure the module's location is in system paths
        if configurations[name].location not in sys.path:
            sys.path.append(str(configurations[name].location))
        # Load and execute the module
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        setattr(addons, name, module)
        _logger.debug(f"Successfully imported module: {name}")
    except Exception as e:
        _logger.error(f"Failed to import module {name}: {e}", exc_info=True)
        sys.exit(-1)


def load_configurations():
    graph = Graph()
    globals()['configurations'] = graph.order_configurations()
    for name in configurations:
        import_module(name)
