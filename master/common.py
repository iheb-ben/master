from typing import Optional
from master.config import arguments
from master import core
import re


def main():
    """
    Main entry point for building, initialising classes and ORM models.
    """
    classes = core.api.compile_classes(core.module.loader.read_all())
    git_repo_manager = core.GitRepoManager() if not arguments['pipeline'] else None
    postgres_manager = classes['master.core.PostgresManager'](arguments.read_parameter('default_db_name'))
    db_structure_manager = classes['master.core.DBStructureManager'](postgres_manager.admin_connection())
    print(db_structure_manager)
    core.orm.build_models()
