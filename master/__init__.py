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
server: Optional[core.server.Server] = None
repositories: Optional[core.git.GitRepoManager] = None
manager: Optional[core.threads.ThreadManager] = None


def main() -> None:
    globals()['manager'] = core.threads.ThreadManager()
    if core.arguments['pipeline']:
        if core.arguments['pipeline_mode'] in (core.parser.PipelineMode.MANAGER.value, core.parser.PipelineMode.NODE.value):
            core.pem.configure()
            globals()['repositories'] = core.git.GitRepoManager()
            repositories.configure()
            if core.arguments['pipeline_mode'] == core.parser.PipelineMode.MANAGER.value:
                manager.add_thread('GIT_MANAGER', repositories.run)
            globals()['server'] = core.server.Server()
    else:
        globals()['server'] = core.server.Server()
    if server:
        core.modules.load_configurations()
        manager.start_all()
        for key, name in {
            'mode': 'Environment',
            'node_type': 'Node Type',
            'os_name': 'OS Name',
            'os_version': 'OS Version',
            'version': 'Version',
        }.items():
            _logger.info(f'{name}: {core.signature[key]}')
        _logger.info('ERP started')
        server.run()
        while manager.is_alive():
            time.sleep(1)
        _logger.info('ERP stopped')
