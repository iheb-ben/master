from typing import Optional
from master.config import arguments
from master import core
import re


# Global manager variables
postgres_manager: Optional[core.db.PostgresManager] = None
mongo_db_manager: Optional[core.db.MongoDBManager] = None
git_repo_manager = core.GitRepoManager() if not arguments['pipeline'] else None


def main():
    """
    Main entry point for building, initialising classes and ORM models.
    """
    core.api.compile_classes()
    global postgres_manager
    postgres_manager = core.PostgresManager(arguments.read_parameter('default_db_name'))
    db_structure_manager = core.DBStructureManager(postgres_manager.admin_connection())
    print(db_structure_manager)
    core.orm.build_models()
