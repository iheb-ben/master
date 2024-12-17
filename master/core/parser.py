import argparse
import datetime
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Optional, TypedDict, List, Set, Union

from master.tools.enums import Enum
from master.tools.generator import generate_unique_string
from master.tools.paths import temporairy_directory
from master.tools.system import find_available_port, port_in_range

# Configure logging
logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)


class Mode(str, Enum):
    """Enum for defining ERP modes."""
    STAGING = 'staging'
    PRODUCTION = 'production'


class PipelineMode(str, Enum):
    """Enum for defining pipeline modes."""
    NODE = 'node'
    MANAGER = 'manager'
    INSTANCE = 'instance'


class LoggerType(str, Enum):
    """Enum for logger types."""
    CRITICAL = 'critical'
    ERROR = 'error'
    WARNING = 'warning'
    INFO = 'info'
    DEBUG = 'debug'

    @classmethod
    def to_logging_level(cls, value: str) -> int:
        """Converts value log level to `logging` module level."""
        return getattr(logging, LoggerType.from_value(value).value.upper(), logging.INFO)


class ArgumentsDict(TypedDict, total=False):
    """TypedDict for all configurable arguments."""
    mode: str
    log_file: str
    log_level: str
    master_password: str
    jwt_secret: str
    origins: Optional[str]
    port: int
    addons_paths: Union[List[str], str, None]
    directory: str
    thread_stack_size: int
    pipeline: bool
    pipeline_mode: str
    pipeline_port: int
    pipeline_interval: int
    pipeline_webhook: bool
    db_name: str
    db_host: str
    db_port: int
    db_user: str
    db_password: str
    db_mongo: bool
    db_mongo_security_authorization: bool
    db_mongo_host: str
    db_mongo_port: int
    db_mongo_user: str
    db_mongo_password: str
    git: Union[List[Dict[str, str]], Dict[str, str], None]
    # Computed settings
    logging_level: int
    node_type: str


_unstorable_fields: Set[str] = {'node_type', 'logging_level', 'configuration'}
_path = temporairy_directory() / 'configuration.json'


def load_configuration(path: Path) -> ArgumentsDict:
    """Loads configuration from a JSON file."""
    try:
        if path.exists() and path.is_file() and path.suffix == '.json':
            with open(path, 'r') as file:
                config: ArgumentsDict = json.load(file)
                if isinstance(config, dict):
                    return config
    except (OSError, json.JSONDecodeError) as e:
        _logger.error(f"Failed to load configuration from {path}: {e}")
    return {}


def save_configuration(path: Path, config: ArgumentsDict):
    """Saves arguments to a JSON configuration file."""
    try:
        with open(path, 'w') as file:
            json.dump({k: v for k, v in config.items() if k not in _unstorable_fields}, file, indent=4, sort_keys=True)
    except OSError as e:
        _logger.error(f"Failed to save configuration to {path}: {e}")


class ParsedArguments:
    """
    Encapsulates parsed command-line arguments and manages configurations.
    """
    __slots__ = ('master_password', 'jwt_secret', 'arguments', '_ignore_keys')

    def __init__(self, configuration_path: Optional[str] = None):
        self._ignore_keys: Set[str] = set()
        self.arguments = ArgumentsDict()
        # Load configuration from input JSON file
        if configuration_path:
            self.update_configuration(load_configuration(Path(configuration_path)))
        # Load default configuration file
        arguments = load_configuration(_path)
        self.master_password = arguments.get('master_password') or generate_unique_string(20)
        self.jwt_secret = arguments.get('jwt_secret') or generate_unique_string(255)
        arguments_keys = ArgumentsDict.__annotations__.keys()
        for key, value in arguments.items():
            if key in arguments_keys:
                self.arguments.setdefault(key, value)

    def update_configuration(self, arguments: ArgumentsDict):
        """Updates configuration arguments dynamically."""
        for key in ArgumentsDict.__annotations__.keys():
            if key in arguments and key not in self._ignore_keys:
                # noinspection PyTypedDict
                self.arguments[key] = arguments[key]
                self._ignore_keys.add(key)

    def check(self):
        """Validates certain arguments for correctness."""
        # Validate paths
        for path_key in ['log_file']:
            # noinspection PyTypedDict
            path = self.arguments.get(path_key)
            if path and not Path(str(path)).is_file():
                raise ValueError(f'Invalid file path for "{path_key}": {path}')
        for directory_key in ['directory']:
            # noinspection PyTypedDict
            path = self.arguments.get(directory_key)
            if path and not Path(str(path)).is_dir():
                raise ValueError(f'Invalid directory path for "{directory_key}": {path}')
        for addons_path_key in ['addons_paths']:
            # noinspection PyTypedDict
            paths = self.arguments.get(addons_path_key)
            if isinstance(paths, list):
                for path in paths:
                    if not Path(str(path)).is_dir():
                        raise ValueError(f'Invalid directory path for "{addons_path_key}": {path}')
        # Validate port ranges
        validate_ports = ['port', 'db_port', 'db_mongo_port']
        if self.arguments['pipeline'] and self.arguments['pipeline_mode'] == PipelineMode.NODE.value:
            validate_ports.append('pipeline_port')
        for port_key in validate_ports:
            # noinspection PyTypedDict
            port = self.arguments.get(port_key)
            if port and not port_in_range(int(port)):
                raise ValueError(f'Invalid port for "{port_key}": {port}')
        # Validate positive non-null values
        for integer_key in ['pipeline_interval']:
            # noinspection PyTypedDict
            integer = self.arguments.get(integer_key) or 1
            if integer and integer < 0:
                raise ValueError(f'Parameter "{integer_key}" must be strictly positive number')

    def compute(self):
        """Computes derived settings."""
        if self.arguments.get('pipeline'):
            self.arguments['node_type'] = self.arguments.get('pipeline_mode') or 'basic'
        else:
            self.arguments['node_type'] = 'basic'
        if self.arguments['mode'] == Mode.STAGING.value:
            self.arguments['logging_level'] = logging.DEBUG
        else:
            self.arguments['logging_level'] = LoggerType.to_logging_level(self.arguments['log_level'])

    def save(self):
        """Saves current arguments to the default JSON configuration file."""
        save_configuration(_path, self.arguments)


def _default_log_file_path(mode: str) -> str:
    filename = f'{datetime.datetime.utcnow().strftime("%Y_%m_%d")}.log'
    return str(temporairy_directory() / 'logs' / mode / filename)


class ArgumentParser:
    """Parses and validates command-line arguments."""
    def __init__(self):
        self._parser = argparse.ArgumentParser(
            prog='MASTER',
            description='All-in-one ERP management tool'
        )
        self._initialize_arguments()

    def _initialize_arguments(self):
        """Defines all command-line arguments."""
        # General arguments
        self._parser.add_argument('--mode', choices=[e.value for e in Mode], default=Mode.STAGING.value, help='ERP mode')
        self._parser.add_argument('--configuration', type=str, help='Path to ERP configuration file in JSON format')
        self._parser.add_argument('--master-password', type=str, help='Master password')
        self._parser.add_argument('--addons-paths', nargs='+', type=str, help='Addons paths')
        self._parser.add_argument('--directory', type=str, default=str(temporairy_directory()), help='Path to ERP directory folder')
        self._parser.add_argument('--log-file', type=str, help='Log file path')
        self._parser.add_argument('--log-level', choices=[e.value for e in LoggerType], default=LoggerType.INFO.value, help='Log level')
        self._parser.add_argument('--port', type=int, default=find_available_port(9000), help='ERP port')
        self._parser.add_argument('--jwt-secret', type=str, help='JWT secret key')
        self._parser.add_argument('--origins', type=str, help='Allow origins')
        self._parser.add_argument('--thread-stack-size', type=int, default=2 * 1024 * 1024, help='The maximun thread stack size allowed for the system')
        # Pipeline settings
        pipeline_group = self._parser.add_argument_group('Pipeline Configuration', 'Pipeline-related settings')
        pipeline_group.add_argument('--pipeline', action='store_true', default=True, help='Enable pipeline mode')
        pipeline_group.add_argument('--pipeline-mode', choices=[e.value for e in PipelineMode if e != PipelineMode.INSTANCE], default=PipelineMode.MANAGER.value, help='Pipeline mode')
        pipeline_group.add_argument('--pipeline-port', type=int, default=find_available_port(9001), help='Pipeline node port')
        pipeline_group.add_argument('--pipeline-interval', type=int, default=10, help='Periode (Seconds) of checking the git repositories')
        pipeline_group.add_argument('--pipeline-webhook', action='store_true', default=False, help='Use webhooks instead of custom watcher for any repo changes')
        # Database settings
        db_group = self._parser.add_argument_group('Database Configuration', 'Database-related settings')
        db_group.add_argument('--db-name', default='master', help='Database name')
        db_group.add_argument('--db-host', default='localhost', help='Database host')
        db_group.add_argument('--db-port', type=int, default=5432, help='Database port')
        db_group.add_argument('--db-user', default='postgres', help='Database username')
        db_group.add_argument('--db-password', default='postgres', help='Database user password')
        db_group.add_argument('--db-mongo', action='store_true', help='Enable MongoDB connection')
        db_group.add_argument('--db-mongo-security-authorization', action='store_true', help='Enable MongoDB authorization')
        db_group.add_argument('--db-mongo-host', default='localhost', help='MongoDB host')
        db_group.add_argument('--db-mongo-port', type=int, default=27017, help='MongoDB port')
        db_group.add_argument('--db-mongo-user', default='mongo', help='MongoDB username')
        db_group.add_argument('--db-mongo-password', default='mongo', help='MongoDB password')

    def parse(self) -> ArgumentsDict:
        """Parses command-line arguments and returns the parsed configuration."""
        namespace = self._parser.parse_args(sys.argv[1:])
        parsed = ParsedArguments(namespace.configuration)
        parsed.update_configuration(vars(namespace))
        # Correct mandatory values
        if not parsed.arguments.get('git'):
            parsed.arguments['git'] = []
        if not isinstance(parsed.arguments['git'], list):
            parsed.arguments['git'] = [parsed.arguments['git']]
        if not parsed.arguments.get('addons_paths'):
            parsed.arguments['addons_paths'] = []
        if not isinstance(parsed.arguments['addons_paths'], list):
            parsed.arguments['addons_paths'] = [parsed.arguments['addons_paths']]
        if not parsed.arguments.get('master_password'):
            parsed.arguments['master_password'] = parsed.master_password
        if not parsed.arguments.get('jwt_secret'):
            parsed.arguments['jwt_secret'] = parsed.jwt_secret
        if not parsed.arguments['pipeline_interval'] or parsed.arguments['pipeline_interval'] <= 0:
            parsed.arguments['pipeline_interval'] = 1
        if not parsed.arguments['log_file']:
            current = parsed.arguments['pipeline'] and parsed.arguments['pipeline_mode'] or PipelineMode.INSTANCE.value
            parsed.arguments['log_file'] = _default_log_file_path(current)
        if parsed.arguments['log_file']:
            _create_file(Path(parsed.arguments['log_file']))
        if parsed.arguments['directory']:
            _create_directory(Path(parsed.arguments['directory']))
        parsed.check()
        parsed.save()
        parsed.compute()
        return parsed.arguments


def _create_file(path: Path):
    if not path.is_file():
        _create_directory(path.parent)
        path.touch()


def _create_directory(path: Path):
    if not path.is_dir():
        path.mkdir(parents=True)
