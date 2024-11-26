import signal
import traceback
import sys
import logging
from typing import Optional

from . import addons
from . import tools
from . import api
from . import core

_logger = logging.getLogger(__name__)
repositories: Optional[core.git.GitRepoManager] = None


def main():
    if core.arguments['help']:
        core.parser.ArgumentParser().help()
        sys.exit(1)
    core.pem.configure()
    manager = core.threads.ThreadManager()
    if core.arguments['pipeline']:
        if core.arguments['pipeline_mode'] == core.parser.PipelineMode.MANAGER.value:
            globals()['repositories'] = core.git.GitRepoManager()
            manager.add_thread('GIT_MANAGER', repositories.run)
        elif core.arguments['pipeline_mode'] == core.parser.PipelineMode.NODE.value:
            # TODO: trigger a small server for managing the ERP instance, use pipeline_port
            pass
    for key, name in {
        'mode': 'Node',
        'node_type': 'Node Type',
        'os_name': 'OS Name',
        'os_version': 'OS Version',
        'version': 'Version',
    }.items():
        _logger.info(f'{name}: {core.signature[key]}')
    _logger.info(f'GIT token for webhook: {core.git.token}')
    try:
        manager.start_all()
        manager.wait_for_all()
    except KeyboardInterrupt:
        if not core.threads.stop_event.is_set():
            core.threads.stop_event.set()
