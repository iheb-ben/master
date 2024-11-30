import signal
import time
import traceback
import sys
import logging
from typing import Optional

from . import pip

pip.install_requirements('./requirements.txt', True)

from . import addons
from . import tools
from . import api
from . import core

_logger = logging.getLogger(__name__)
repositories: Optional[core.git.GitRepoManager] = None
manager: Optional[core.threads.ThreadManager] = None


def main():
    if core.arguments['help']:
        core.parser.ArgumentParser().help()
        sys.exit(0)
    globals()['manager'] = core.threads.ThreadManager()
    if core.arguments['pipeline']:
        core.pem.configure()
        globals()['repositories'] = core.git.GitRepoManager()
        repositories.configure()
        if core.arguments['pipeline_mode'] == core.parser.PipelineMode.MANAGER.value:
            manager.add_thread('GIT_MANAGER', repositories.run)
        elif core.arguments['pipeline_mode'] == core.parser.PipelineMode.NODE.value:
            manager.add_thread('GIT_NODE', repositories.run)
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
    manager.start_all()
    while manager.is_alive():
        time.sleep(1)
    _logger.info('ERP stopped')
