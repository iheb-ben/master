import traceback
import sys
from . import tools
from . import addons
from . import api
from . import core
import logging

_logger = logging.getLogger(__name__)


def print_details():
    for key, name in {
        'mode': 'Node',
        'node_type': 'Node Type',
        'os_name': 'OS Name',
        'os_version': 'OS Version',
        'version': 'Version',
    }.items():
        _logger.info(f'{name}: {core.signature[key]}')


def main():
    if core.arguments['help']:
        core.parser.ArgumentParser().help()
        sys.exit(1)
    core.pem.configure()
    print_details()
