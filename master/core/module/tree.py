from collections import OrderedDict
from typing import Dict, List, Iterable, Tuple
from master.core.module import Configuration


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


OrderedConfiguration = Dict[str, Configuration]


class Tree:
    """
    Represents a dependency tree for managing module configurations.
    Attributes:
        _default (str): The default module name.
        _modules (Dict[str, Node]): Mapping of module names to their corresponding Node objects.
        _incorrect (List[str]): List of missing dependencies that could not be resolved.
    """
    __slots__ = ('_default', '_modules', '_incorrect')

    def __init__(self, configuration: Configuration):
        self._default = configuration.name
        self._modules: Dict[str, Node] = {configuration.name: Node(configuration)}
        self._incorrect: List[str] = []

    def build_node(self, configuration: Configuration):
        """
        Builds a node for a given module configuration if it doesn't already exist.
        Args:
            configuration (Configuration): The module configuration to add.
        """
        if configuration.name not in self._modules:
            self._modules[configuration.name] = Node(configuration)

    def build_links(self, configurations: Iterable[Configuration]):
        """
        Establishes parent-child relationships based on module dependencies.
        Args:
            configurations (Iterable[Configuration]): A list of module configurations to process.
        """
        for configuration in configurations:
            for dependency in configuration.depends:
                if dependency not in self._modules:
                    self._incorrect.append(dependency)
                    try:
                        configuration.depends.remove(dependency)
                    except ValueError:
                        continue
                else:
                    self._modules[dependency].add_child(self._modules[configuration.name])
        for node in self._modules.values():
            if node.name == self._default:
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
            Tuple[int, int, str]: A tuple used to sort nodes by the number of parents, sequence, and name.
        """
        return node.factor, node.sequence, len(node.parents), node.name

    def order_nodes(self, configurations: Dict[str, Configuration]) -> Tuple[List[str], OrderedConfiguration]:
        """
        Orders nodes based on dependencies and sequence.
        Args:
            configurations (Dict[str, Configuration]): A mapping of module names to configurations.
        Returns:
            Tuple[List[str], List[Configuration]]:
                - A list of missing dependencies.
                - An ordered list of configurations.
        """
        reversed_depends: Dict[str, List[str]] = {}
        ordered_names: List[str] = []
        ordered_configurations: Dict[str, Configuration] = OrderedDict()
        for node in sorted(self._collect_all_nodes(self._modules[self._default]), key=self._sort_all_nodes):
            ordered_configurations[node.name] = configurations[node.name]
            reversed_depends[node.name] = [_node.name for _node in node.children]
            ordered_names.append(node.name)
        for configuration in ordered_configurations.values():
            configuration.reversed_depends = reversed_depends[configuration.name]
            configuration.depends = [name for name in ordered_names if name in configuration.depends]
        return self._incorrect, ordered_configurations

    def __repr__(self) -> str:
        """Returns a string representation of the Tree instance."""
        return f'Tree({self._default}, {len(self._modules.keys())})'
