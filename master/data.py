from typing import Optional
from master.config import arguments
from master import core
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


def main():
    """
    Main entry point for building classes and ORM models.
    """
    core.api.compile_classes()
    initialise_values()
