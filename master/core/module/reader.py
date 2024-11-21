import subprocess
import sys
from os import listdir
from pathlib import Path
from typing import Dict, Any, Optional, Generator
import json
from master.config.logging import get_logger
from master.config import arguments
from master.core.module import Configuration

_logger = get_logger(__name__)


def iterate_addons_paths() -> Generator[Path, None, None]:
    """
    Iterates through all addon paths specified in the configuration.
    Yields:
        Path: A valid addons directory path.
    """
    base_path = Path('./master/addons').absolute().resolve()
    current_paths = [Path(p).absolute().resolve() for p in arguments['addons']]
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
    assert arguments['master_configuration_name'], 'Missing required system field "master_configuration_name"'
    config_file = module_path / arguments['master_configuration_name']
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


def read_configurations() -> Dict[str, Configuration]:
    """
    Reads and parses configurations for all valid modules in the addon paths.
    Returns:
        Dict[str, Configuration]: An iterable of Configuration objects.
    """
    configurations: Dict[str, Configuration] = {}
    for addons_path in iterate_addons_paths():
        requirements_file = addons_path / 'requirements.txt'
        if not install_requirements(requirements_file):
            continue
        is_empty = True
        for module_name in listdir(addons_path):
            module_path = addons_path / module_name
            if module_path.is_file() or module_name == '__pycache__' or module_name.startswith('.'):
                continue
            configuration_data = read_module_configuration(module_path)
            if configuration_data is not None:
                configuration_data['path'] = module_path
                configurations[module_name] = Configuration(**configuration_data)
                is_empty = False
            else:
                _logger.warning(f'Ignored invalid module: {module_name}')
        if is_empty:
            _logger.warning(f'No valid modules found in: {addons_path}')
    return configurations
