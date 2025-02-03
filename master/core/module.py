import importlib
import sys
from pathlib import Path
from typing import Dict, List
from psycopg2.sql import SQL
from master.core.database.cursor import Cursor
from master.core.tools.config import environ
from master.core.tools.files import iterate_directory, decompress_zip, TEMP_ADDONS_FOLDER

AddonsPaths = Dict[str, Path]
_init_file_name = '__init__.py'
_config_file_name = '_.json'


def is_addon_package(path_obj: Path):
    init_file_exists = path_obj.joinpath(_init_file_name).is_file()
    config_file_exists = path_obj.joinpath(_config_file_name).is_file()
    check_name = '__pycache__' not in path_obj.parts and not path_obj.name.startswith('_')
    return init_file_exists and config_file_exists and check_name


def modules_paths() -> AddonsPaths:
    found_addons = {}
    for current in reversed(environ['ADDONS_PATHS']):
        for path_obj in iterate_directory(current):
            if path_obj.suffix == '.zip':
                path_obj = decompress_zip(path_obj, TEMP_ADDONS_FOLDER / path_obj.stem)
            elif path_obj.suffix:
                continue
            if not is_addon_package(path_obj):
                continue
            if path_obj.name not in found_addons:
                found_addons[path_obj.name] = path_obj
    return found_addons


def attach_order(paths: AddonsPaths, load_order: List[str]):
    for name in load_order:
        if name not in paths:
            continue
        package_dir = paths[name]
        if str(package_dir) not in sys.path:
            sys.path.append(str(package_dir))
        module_name = f'master.addons.{name}'
        importlib.import_module(module_name)


def select_addons(cursor: Cursor):
    update_modules = environ['UPDATE_ADDONS'] or []
    default_select = 'SELECT meta_name FROM ir_module WHERE state'
    return environ['BASE_ADDONS'] or [row[0] for row in cursor.execute(
        sql=SQL(f"{default_select} IN ('installed', 'to_update')"),
        raise_error=False,
        default=[['base'], ['web']],
    )], list(set([row[0] for row in cursor.execute(
        sql=SQL(f"{default_select} = 'to_update'"),
        raise_error=False,
        default=[],
    )] + update_modules))
