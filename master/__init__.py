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
repositories: Optional[core.git.GitRepoManager] = core.git.GitRepoManager()


def main():
    if core.arguments['help']:
        core.parser.ArgumentParser().help()
        sys.exit(1)
    core.pem.configure()
    manager = core.threads.ThreadManager()
    if not core.arguments['pipeline']:
        globals()['repositories'] = None
    else:
        if core.arguments['pipeline_mode'] == core.parser.PipelineMode.MANAGER.value:
            manager.add_thread('GIT_MANAGER', repositories.run)
        elif core.arguments['pipeline_mode'] == core.parser.PipelineMode.NODE.value:
            # TODO: trigger a small server for managing the ERP instance, use pipeline_port
            pass
    for key, name in {
        'mode': 'Environment',
        'node_type': 'Node Type',
        'os_name': 'OS Name',
        'os_version': 'OS Version',
        'version': 'Version',
    }.items():
        _logger.info(f'{name}: {core.signature[key]}')
    try:
        manager.start_all()
        manager.wait_for_all()
    except KeyboardInterrupt:
        if not core.threads.stop_event.is_set():
            core.threads.stop_event.set()
