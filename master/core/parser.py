import argparse
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Optional, TypedDict, List

# Custom tools
from master.api import classproperty
from master.tools.enums import Enum
from master.tools.collection import is_complex_iterable
from master.tools.generator import generate_unique_string
from master.tools.paths import temporairy_directory
from master.tools.system import find_available_port

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
    help: bool
    mode: str
    log_file: str
    log_level: str
    master_password: str
    pipeline: bool
    pipeline_mode: str
    node_type: Optional[str]
    db_name: str
    db_host: str
    db_port: int
    db_user: str
    db_password: str
    db_mongo: bool
    db_mongo_host: str
    db_mongo_port: int
    db_mongo_user: str
    db_mongo_password: str


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
        ignore_keys = ['help']
        with open(path, 'w') as file:
            json.dump({k: v for k, v in config.items() if k not in ignore_keys}, file, indent=4)
    except OSError as e:
        _logger.error(f"Failed to save configuration to {path}: {e}")


# noinspection PyTypedDict,PyMethodParameters
class ParsedArguments:
    """
    Encapsulates parsed command-line arguments and manages configurations.
    """
    __slots__ = ('arguments', '_path', '_ignore')

    def __init__(self, configuration_path: Optional[str] = None):
        self._ignore: List[str] = []
        self._path = temporairy_directory().joinpath('configuration.json')
        self.arguments: ArgumentsDict = {}

        # Load configurations from JSON file or temporary directory
        if configuration_path:
            config = load_configuration(Path(configuration_path))
            self._ignore.extend([name for name in config.keys() if name in self.arguments_names])
            self._merge_configuration(config)
        self._merge_configuration(load_configuration(self._path))

        # Add 'help' flag
        self.arguments['help'] = any(v in sys.argv for v in ['-h', '--help'])

    def _merge_configuration(self, config: ArgumentsDict):
        """Merge a configuration dictionary into the arguments."""
        for key, value in config.items():
            if key in self.arguments_names:
                self.arguments.setdefault(key, value)

    def update_configuration(self, config: ArgumentsDict):
        """Updates configuration arguments dynamically."""
        for key, value in config.items():
            if key in self.arguments_names and key not in self._ignore:
                self.arguments[key] = value

    def check(self):
        """Validates certain arguments for correctness."""
        # Validate paths
        for path_key in ['log_file']:
            path = self.arguments.get(path_key)
            if path and not Path(str(path)).is_file():
                raise ValueError(f'Invalid file path for "{path_key}": {path}')

        # Validate port ranges
        for port_key in ['port', 'db_port', 'db_mongo_port']:
            port = self.arguments.get(port_key)
            if port and not (1 <= int(port) <= 65535):
                raise ValueError(f'Invalid port for "{port_key}": {port}')

    def compute(self):
        """Computes derived settings."""
        if self.arguments.get('pipeline'):
            self.arguments['node_type'] = self.arguments.get('pipeline_mode')
        else:
            self.arguments['node_type'] = 'basic'
        self.arguments['log_level'] = LoggerType.to_logging_level(self.arguments['log_level'])

    @classproperty
    def arguments_names(cls) -> List[str]:
        """Retrieves the list of valid argument names from `ArgumentsDict`."""
        return list(ArgumentsDict.__annotations__.keys())

    def save(self):
        """Saves current arguments to the default JSON configuration file."""
        save_configuration(self._path, self.arguments)


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
        self._parser.add_argument('--log-file', type=str, default=str(temporairy_directory().joinpath('master.log')), help='Log file path')
        self._parser.add_argument('--log-level', choices=[e.value for e in LoggerType], default=LoggerType.INFO.value, help='Log level')
        self._parser.add_argument('--port', type=int, default=find_available_port(9000), help='ERP port')

        # Pipeline settings
        pipeline_group = self._parser.add_argument_group('Pipeline Configuration', 'Pipeline-related settings')
        pipeline_group.add_argument('--pipeline', action='store_true', default=True, help='Enable pipeline mode')
        pipeline_group.add_argument('--pipeline-mode', choices=[e.value for e in PipelineMode], default=PipelineMode.NODE.value, help='Pipeline mode')

        # Database settings
        db_group = self._parser.add_argument_group('Database Configuration', 'Database-related settings')
        db_group.add_argument('--db-name', default='master', help='Database name')
        db_group.add_argument('--db-host', default='localhost', help='Database host')
        db_group.add_argument('--db-port', type=int, default=5432, help='Database port')
        db_group.add_argument('--db-user', default='postgres', help='Database username')
        db_group.add_argument('--db-password', default='postgres', help='Database user password')
        db_group.add_argument('--db-mongo', action='store_true', help='Enable MongoDB connection')
        db_group.add_argument('--db-mongo-host', default='localhost', help='MongoDB host')
        db_group.add_argument('--db-mongo-port', type=int, default=27017, help='MongoDB port')
        db_group.add_argument('--db-mongo-user', default='mongo', help='MongoDB username')
        db_group.add_argument('--db-mongo-password', default='mongo', help='MongoDB password')

    def parse(self) -> ArgumentsDict:
        """Parses command-line arguments and returns the parsed configuration."""
        namespace = self._parser.parse_args(sys.argv[1:])
        parsed_arguments = ParsedArguments(namespace.configuration)
        parsed_arguments.update_configuration(vars(namespace))
        parsed_arguments.check()
        parsed_arguments.save()
        parsed_arguments.compute()
        return parsed_arguments.arguments

    def help(self):
        """Displays help information."""
        self._parser.print_help()
