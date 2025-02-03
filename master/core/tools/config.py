import os
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Optional, Dict
from dotenv import load_dotenv
from typing import Any
from .files import TEMP_FOLDER, create_path, to_path
from .typing import cast_string

parser = ArgumentParser(prog='MASTER', description='MASTER ERP tool')
general_setting = parser.add_argument_group(title='HTTP settings', description='Server full settings')
general_setting.add_argument('--env-path', dest='dotenv_path', default='./.env', help='Default env file location')
general_setting.add_argument('--directory', default=str(TEMP_FOLDER), help='Default ERP directory for storing data')
general_setting.add_argument('--addons-paths', nargs='+', help='Default ERP addons paths')
general_setting.add_argument('-e', '--env', dest='env', default='development', help='Default env')
general_setting.add_argument('-p', '--port', type=int, default=8080, help='HTTP port')
db_setting = parser.add_argument_group(title='Database Settings', description='Database full settings')
db_setting.add_argument('-d', '--database-name', dest='pg_name', default='master', help='Default DB name')
db_setting.add_argument('--database-port', dest='pg_port', type=int, default=5432, help='Default DB port')
db_setting.add_argument('--database-host', dest='pg_host', default='localhost', help='Default DB host')
db_setting.add_argument('--database-user', dest='pg_user', default='postgres', help='Default DB user')
db_setting.add_argument('--database-password', dest='pg_password', default='postgres', help='Default DB password')
db_setting.add_argument('--database-min', dest='db_min_conn', type=int, default=2, help='Default DB minimum connections number')
db_setting.add_argument('--database-max', dest='db_max_conn', type=int, default=20, help='Default DB maximum connections number')
environ: Dict[str, Any] = {}


def main():
    arguments = parser.parse_args(sys.argv[1:])
    dotenv_path: Optional[Path] = Path(arguments.dotenv_path).absolute().resolve()
    if not dotenv_path.is_file():
        dotenv_path = None
    load_dotenv(dotenv_path)
    for key, value in vars(arguments).items():
        env_key = key.upper()
        env_value = os.environ.get(env_key)
        if key == 'dotenv_path':
            continue
        elif key == 'addons_paths':
            env_value = [o for o in map(lambda p: to_path(p), set(filter(lambda v: v, (env_value or '').split(',')))) if o.is_dir()]
            value = [o for o in map(lambda p: to_path(p), set(value or [])) if o.is_dir()]
        elif key == 'directory':
            env_value = env_value and str(create_path(env_value)) or None
            value = str(create_path(value))
        environ.setdefault(env_key, cast_string(env_value, type(value)) or value)
    environ.setdefault('HELP_MODE', any(p in sys.argv for p in ('-h', '--help')))
    return environ
