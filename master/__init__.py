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


def main() -> None:
    globals()['manager'] = core.threads.ThreadManager()
    if core.arguments['pipeline']:
        core.pem.configure()
        globals()['repositories'] = core.git.GitRepoManager()
        repositories.configure()
        if not core.arguments['pipeline_webhook']:
            if core.arguments['pipeline_mode'] == core.parser.PipelineMode.MANAGER.value:
                manager.add_thread('GIT_MANAGER', repositories.run)
            elif core.arguments['pipeline_mode'] == core.parser.PipelineMode.NODE.value:
                # TODO: Create a small server that runs and terminates the instance based on the received commands
                pass
    # TODO: Create the server then add it to the threads manager
    if manager.threads:
        core.modules.load_configurations()
        for key, name in {
            'mode': 'Environment',
            'node_type': 'Node Type',
            'os_name': 'OS Name',
            'os_version': 'OS Version',
            'version': 'Version',
        }.items():
            _logger.info(f'{name}: {core.signature[key]}')
        manager.start_all()
        _logger.info('ERP started')
        while manager.is_alive():
            time.sleep(1)
        _logger.info('ERP stopped')
