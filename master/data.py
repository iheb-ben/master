from typing import Optional
from master.config.parser import arguments
from master.core.api import Class
from master import core
from master.tools.misc import call_classmethod
import re


# Global manager variables
postgres_manager: Optional[core.db.PostgresManager] = None
mongo_db_manager: Optional[core.db.MongoDBManager] = None
db_structure_manager: Optional[core.orm.DBStructureManager] = None
git_repo_manager: Optional[core.repository.GitRepoManager] = None


def initialise_values():
    global postgres_manager, db_structure_manager
    postgres_manager = core.PostgresManager(arguments.read_parameter('default_db_name'))
    db_structure_manager = core.DBStructureManager(postgres_manager.admin_connection())
