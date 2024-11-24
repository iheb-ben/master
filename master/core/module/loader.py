from importlib.util import spec_from_file_location, module_from_spec
from typing import Iterable, List
from master import addons
from master.config.logging import get_logger
from master.config import arguments
from master.core.db import PostgresManager
from master.core.module import Configuration, ConfigurationMode
from master.core.module.tree import OrderedConfiguration
from master.exceptions.db import DatabaseSessionError
from master.tools.misc import clean_end_of_line
import psycopg2
import sys

_logger = get_logger(__name__)
pending_update_modules: List[str] = []
installed_modules: List[str] = []


def read_all():
    return installed_modules + pending_update_modules


def check_condition(configuration: Configuration) -> bool:
    """
    Checks if a module should be auto-installed based on the pipeline and configuration mode.
    Args:
        configuration (Configuration): The module configuration to check.
    Returns:
        bool: True if the module should be auto-installed, False otherwise.
    """
    pipeline_mode = arguments['pipeline']
    if not pipeline_mode or (pipeline_mode and configuration.mode in [ConfigurationMode.BOTH, ConfigurationMode.PIPELINE]):
        return configuration.auto_install
    return False


def reorder_module_names(modules: List[str]):
    from master.core.module import configurations
    return [name for name in configurations if name in modules]


def default_modules():
    """
    Retrieves the list of default modules from the database or fallback to local configurations.
    """
    from master.core.module import configurations
    global installed_modules, pending_update_modules
    try:
        manager = PostgresManager()
        with manager.admin_connection().cursor() as cursor:
            cursor.execute("SELECT key FROM module_module WHERE state='installed';")
            installed_modules = [row[0] for row in cursor.fetchall()]
            cursor.execute("SELECT key FROM module_module WHERE state='to_update';")
            pending_update_modules = [row[0] for row in cursor.fetchall()]
            _logger.debug(f"Retrieved installed modules from the database: {installed_modules}")
    except (psycopg2.Error, DatabaseSessionError) as e:
        _logger.warning(f"Could not retrieve default modules from database: {clean_end_of_line(str(e))}")
    finally:
        if not installed_modules:
            _logger.warning("Falling back to local configurations for default modules.")
            installed_modules = [name for name in configurations if check_condition(configurations[name])]
        else:
            installed_modules = reorder_module_names(installed_modules)
            pending_update_modules = reorder_module_names(pending_update_modules)


def import_module(name: str):
    """
    Dynamically imports a module and its dependencies.
    Args:
        name (str): The name of the module to import.
    """
    from master.core.module import configurations
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
