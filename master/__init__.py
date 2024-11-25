import signal
import traceback
import sys
from typing import Optional

from . import tools
from . import addons
from . import api
from . import core
import logging

_logger = logging.getLogger(__name__)
git_manager: Optional[core.git.GitRepoManager] = None


def print_details():
    for key, name in {
        'mode': 'Node',
        'node_type': 'Node Type',
        'os_name': 'OS Name',
        'os_version': 'OS Version',
        'version': 'Version',
    }.items():
        _logger.info(f'{name}: {core.signature[key]}')


def destroy():
    if git_manager:
        _logger.info("Termination signal received. Stopping all watcher processes.")
        git_manager.stop_watchers()


def main():
    if core.arguments['help']:
        core.parser.ArgumentParser().help()
        sys.exit(1)
    core.pem.configure()
    if core.arguments['pipeline'] and core.arguments['pipeline_mode'] == core.parser.PipelineMode.MANAGER.value:
        global git_manager
        git_manager = core.git.GitRepoManager()
    signal.signal(signal.SIGINT, lambda sig, frame: destroy())
    signal.signal(signal.SIGTERM, lambda sig, frame: destroy())
    print_details()
    try:
        tools.system.wait_for_signal()
    except KeyboardInterrupt:
        destroy()
