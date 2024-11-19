import traceback
from typing import Optional
from . import exceptions
from . import tools
from . import config
from . import core

_logger = config.logging.get_logger(__name__)
pg_manager: Optional[core.db.PostgresManager] = None
mongo_manager: Optional[core.db.MongoDBManager] = None
db_structure_manager: Optional[core.orm.DBStructureManager] = None
git_repository: Optional[core.repository.GitRepoManager] = None


def main():
    if config.parser.arguments.show_helper():
        exit(1)
    _logger.info(f"Master Password: {config.parser.arguments.configuration['master_password']}")
    config.parser.arguments.save_configuration()
    core.db.main()
    core.module.attach_modules(True)
    if config.parser.arguments.configuration['pipeline']:
        core.pipeline.main()
    else:
        core.server.main()
