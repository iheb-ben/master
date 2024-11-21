from . import parser
from master.tools.ip import get_public_ip, get_private_ip, get_mac_address
from master.tools.misc import temporairy_directory
from pathlib import Path
import platform
import sys

# Global variable to store parsed arguments
arguments = parser.parse_arguments()
# Basic system settings
signature = {
    'mode': arguments.read_parameter('node_type').value,
    'os_name': platform.system(),
    'os_release': platform.release(),
    'os_version': platform.version(),
    'os_architecture': platform.architecture()[0],
    'public_ip': get_public_ip(False),
    'private_ip': get_private_ip(),
    'mac_address': get_mac_address(),
    'python': platform.python_version(),
    'version': 1,
}

from . import logging

_logger = logging.get_logger(__name__)


def system_directory() -> Path:
    """
    Determines the system's directory for storing files.
    - If the configuration includes a `store_folder` key, its value is used as the directory.
    - If `store_folder` is not set, a temporary directory is used instead.
    Returns:
        Path: The path to the storage directory.
    """
    store_folder = arguments.get('store_folder', None)
    if not store_folder:
        store_folder = str(temporairy_directory())
    return Path(store_folder)


from . import security


def main():
    """
    Main entry point for configuration loading and initialization.
    """
    if arguments.show_helper():
        sys.exit(1)
    _logger.info(f"Master Password: {arguments['master_password']}")
    arguments.save_configuration()
    security.configure_system()
