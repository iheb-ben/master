from collections import OrderedDict
from pathlib import Path
from typing import Optional, Union, List, Iterable
from master import addons
from master.config import arguments
from master.config.logging import get_logger
from master.tools.collection import OrderedSet
from master.tools.enums import Enum
from master.core.db import PostgresManager
from master.core.structure import ModuleManager
from master.common import git_repo_manager
import sys

configurations = ModuleManager()

from . import reader, tree, loader

_logger = get_logger(__name__)


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


def main():
    """
    Main entry point for module loading and initialization.
    """
    if not arguments['pipeline']:
        git_repo_manager.setup()
    configurations.update(read_modules())
    if not configurations:
        _logger.error('No configurations found. Shutting down.')
        sys.exit(-1)
    loader.default_modules()
    for name in configurations:
        loader.import_module(name)
