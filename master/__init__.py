import signal
import time
import traceback
import sys
import logging
from typing import Optional
from werkzeug.local import LocalProxy

from . import pip

pip.install_requirements('./requirements.txt', True)
request = LocalProxy(lambda: core.endpoints.local.request)

from . import exceptions
from . import addons
from . import tools
from . import api
from . import core

# Global variables
_logger = logging.getLogger(__name__)
server: Optional[core.server.Server] = None
repositories: Optional[core.git.GitRepoManager] = None
thread_manager: Optional[core.threads.ThreadManager] = None
postgres_manager: Optional[core.db.PostgresManager] = None
mongo_db_manager: Optional[core.db.MongoDBManager] = None


def main() -> None:
    globals()['thread_manager'] = core.threads.ThreadManager()
    if core.arguments['pipeline']:
        if core.arguments['pipeline_mode'] in (core.parser.PipelineMode.MANAGER.value, core.parser.PipelineMode.NODE.value):
            core.pem.configure()
            globals()['repositories'] = core.git.GitRepoManager()
            repositories.configure()
            if core.arguments['pipeline_mode'] == core.parser.PipelineMode.MANAGER.value:
                thread_manager.add_thread('GIT_MANAGER', repositories.run)
            globals()['server'] = core.server.Server()
    else:
        globals()['server'] = core.server.Server()
    if server:
        core.db.initialization()
        core.modules.load_configurations()
        thread_manager.start_all()
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
        while thread_manager.is_alive():
            time.sleep(1)
        _logger.info('ERP stopped')
