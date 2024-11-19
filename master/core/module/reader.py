import subprocess
import sys
from os import listdir
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Generator, Iterable
import json
from master.config.logging import get_logger
from master.config.parser import arguments

_logger = get_logger(__name__)


# noinspection GrazieInspection
class Configuration:
    """
    Represents a module configuration.
    Attributes:
        path (str): The path to the module.
        depends (List[str]): List of module dependencies.
        sequence (int): Load sequence of the module.
    """
    __slots__ = ('path', 'depends', 'sequence')

    def __init__(
        self,
        path: str,
        depends: Optional[Union[List[str], str]] = None,
        sequence: Optional[int] = None
    ):
        """
        Initializes a Configuration instance.
        Args:
            path (str): The path to the module.
            depends (Optional[Union[List[str], str]]): Module dependencies, can be a list or a single string.
            sequence (Optional[int]): The load sequence for the module.
        """
        self.path = path
        base_name = arguments.configuration['master_base_addon']
        # Normalize dependencies to a list of non-empty strings
        if depends is None:
            depends = []
        elif isinstance(depends, str):
            depends = [depends]
        if not isinstance(depends, Iterable) or isinstance(depends, bytes):
            raise ValueError(f'Addon {self.name} issue: Dependency format is incorrect in path "{path}"')
        self.depends = [name.strip() for name in depends if name]
        # Determine sequence with fallback logic
        if sequence is None or sequence <= 0:
            sequence = 16
            _logger.warning(f'Addon {self.name} issue: Incorrect or missing addon sequence, set to default 16.')
        self.sequence = sequence
        # Ensure master_base_addon is included as the first dependency
        if base_name and self.name != base_name and base_name not in self.depends:
            self.depends.insert(0, base_name)

    @property
    def name(self) -> str:
        """
        Extracts the module name from its path.
        Returns:
            str: The name of the module.
        """
        assert self.path, 'Module "path" value is required'
        return Path(self.path).name.strip()

    def to_dict(self) -> dict:
        """
        Converts the configuration to a dictionary format.
        Returns:
            dict: A dictionary representation of the configuration.
        """
        return {
            'name': self.name,
            'path': self.path,
            'sequence': self.sequence,
            'depends': self.depends,
        }


def iterate_addons_paths() -> Generator[Path, None, None]:
    """
    Iterates through all addon paths specified in the configuration.
    Yields:
        Path: A valid addons directory path.
    """
    base_path = Path('./master/addons').absolute().resolve()
    current_paths = [Path(p).absolute().resolve() for p in arguments.configuration['addons']]
    if base_path not in current_paths and base_path.exists():
        current_paths.insert(0, base_path)
    elements_found = False
    for addons_path in current_paths:
        if addons_path.exists() and addons_path.is_dir():
            elements_found = True
            yield addons_path
        else:
            _logger.warning(f'Invalid addons path: "{addons_path.absolute().resolve()}"')
    if not elements_found:
        _logger.error('No valid addons paths were found.')


def install_requirements(requirements_path: Path) -> bool:
    """
    Installs requirements from the specified requirements.txt file.
    Args:
        requirements_path (Path): Path to the requirements.txt file.
    Returns:
        bool: True if requirements were installed successfully or if the file does not exist, False otherwise.
    """
    if not requirements_path.exists() or not requirements_path.is_file():
        return True
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'])
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', str(requirements_path)])
        return True
    except subprocess.CalledProcessError as e:
        _logger.error(f"Failed to install requirements: {e}", exc_info=True)
        return False


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
    assert arguments.configuration['master_configuration_name'], 'Missing required system field "master_configuration_name"'
    config_file = module_path / arguments.configuration['master_configuration_name']
    if not config_file.exists():
        return None
    try:
        with config_file.open('r') as file:
            configuration = json.load(file)
        if module_path.joinpath('__init__.py').exists():
            return configuration
    except (OSError, json.JSONDecodeError) as e:
        _logger.error(f'Failed to load configuration for {module_path.name}: {e}')
    return None


def read_configurations(shutdown: bool = False) -> Iterable[Configuration]:
    """
    Reads and parses configurations for all valid modules in the addon paths.
    Args:
        shutdown (bool): If True, exits the application if no configurations are found.
    Returns:
        Iterable[Configuration]: An iterable of Configuration objects.
    """
    configurations: Dict[str, Configuration] = {}
    for addons_path in iterate_addons_paths():
        requirements_file = addons_path / 'requirements.txt'
        if not install_requirements(requirements_file):
            continue
        is_empty = True
        for module_name in listdir(addons_path):
            module_path = addons_path / module_name
            if module_path.is_file():
                continue
            configuration_data = read_module_configuration(module_path)
            if configuration_data is not None:
                configuration_data['path'] = str(module_path)
                configurations[module_name] = Configuration(**configuration_data)
                is_empty = False
            else:
                _logger.warning(f'Ignored invalid module: {module_name}')
        if is_empty:
            _logger.warning(f'No valid modules found in: {addons_path}')
    if not configurations and shutdown:
        _logger.error('No configurations found. Shutting down.')
        sys.exit(-1)
    return configurations.values()
