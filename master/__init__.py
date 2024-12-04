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
    load_modules = False
    globals().update({
        'manager': core.threads.ThreadManager(),
        'server': core.server.Server(),
    })
    if core.arguments['pipeline']:
        core.pem.configure()
        globals()['repositories'] = core.git.GitRepoManager()
        repositories.configure()
        if core.arguments['pipeline_mode'] == core.parser.PipelineMode.MANAGER.value:
            if not core.arguments['pipeline_webhook']:
                manager.add_thread('GIT_MANAGER', repositories.run)
            manager.add_thread('MANAGER_SERVER', server.run)
            load_modules = True
        elif core.arguments['pipeline_mode'] == core.parser.PipelineMode.NODE.value:
            # TODO: use a different server to trigger the restart and the shutdown of the instance
            manager.add_thread('NODE_SERVER', server.run)
    else:
        manager.add_thread('MAIN_SERVER', server.run)
        load_modules = True
    if manager.threads:
        if load_modules:
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
        if len(manager.threads) == 1:
            manager.threads[0].join()
        else:
            while manager.is_alive():
                time.sleep(1)
        _logger.info('ERP stopped')
