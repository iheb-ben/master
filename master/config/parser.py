from master.tools.enums import Enum
from typing import Optional, Union, Any, Type
from master.tools.collection import LastIndexOrderedSet, OrderedSet
from master.tools.misc import generate_unique_string, find_available_port, temporairy_directory, has_method, call_method
import argparse
import os
import sys
import json
import logging


def default_configuration():
    return temporairy_directory().joinpath('configuration.json')


class Mode(Enum):
    """Enum for defining ERP modes."""
    STAGING = 'staging'
    PRODUCTION = 'production'


class PipelineMode(Enum):
    """Enum for defining ERP modes."""
    NODE = 'node'
    MANAGER = 'manager'


class LoggerType(Enum):
    CRITICAL = 'CRITICAL'
    FATAL = 'FATAL'
    ERROR = 'ERROR'
    WARNING = 'WARNING'
    WARN = 'WARN'
    INFO = 'INFO'
    DEBUG = 'DEBUG'
    NOTSET = 'NOTSET'


class ArgumentParser(dict):
    """Handles parsing and storage of system settings and configuration for ERP."""
    __slots__ = ('signature', 'configuration', 'stored')

    def __init__(self, mode: Union[str, Mode], configuration: dict):
        """
        Initializes ArgumentParser with ERP mode and configuration settings.
        Args:
            mode (Union[str, ErpMode]): Operational mode of ERP ('staging' or 'production').
            configuration (dict): ERP configuration settings.
        Raises:
            AssertionError: If mode is not provided.
        """
        super().__init__()
        assert mode, 'Mode cannot be empty'
        if not isinstance(mode, Mode):
            mode = Mode.from_value(mode.lower())
        self.stored = list()
        # Default configuration settings
        self.update(configuration)
        self.add('master_configuration_name', 'configuration.json', str)
        self.add('master_base_addon', 'base', str)
        self.add('master_password', generate_unique_string(20, '<>\'",.:;[]`/\\'), str, True)
        self.add('log_file', str(temporairy_directory().joinpath('MASTER.log')), str)
        self.add('log_level', LoggerType.DEBUG.value, str)
        self.add('db_hostname', 'localhost', str)
        self.add('db_port', 5432, int)
        self.add('db_password', 'postgres', str)
        self.add('db_user', 'postgres', str)
        self.add('db_mongo', False, bool)
        if self['db_mongo']:
            self.add('db_mongo_security_authorization', False, bool)
            self.add('db_mongo_hostname', 'localhost', str)
            self.add('db_mongo_port', 27017, int)
            self.add('db_mongo_password', 'mongo', str)
            self.add('db_mongo_user', 'mongo', str)
        self.add('pipeline', True, bool)
        if self['pipeline']:
            self.add('pipeline_db_name', 'master_pipelines', str)
            self.add('pipeline_port', find_available_port(9002), int)
        else:
            self.add('pipeline_websocket_port', find_available_port(9001), int)
            self.add('db_name', 'master', str)
            self.add('hostname', 'localhost', str)
            self.add('port', find_available_port(9000), int)
            self.add('websocket_port', find_available_port(9002), int)
        self.add('enviroment', mode.value, str)
        self.add('git', [], list)
        self.add('addons', [], list)
        # Ensure unique sets for 'addons' and 'git' settings
        self['addons'] = LastIndexOrderedSet(self['addons'])
        self['git'] = OrderedSet(self['git'])

    def _parameter_node_type(self) -> PipelineMode:
        if self['pipeline']:
            return PipelineMode.MANAGER
        else:
            return PipelineMode.NODE

    def _parameter_default_db_name(self) -> str:
        if self['pipeline']:
            return self['pipeline_db_name']
        else:
            return self['db_name']

    def _parameter_mongo_db_uri(self, username: Optional[str] = None, password: Optional[str] = None, database_name: Optional[str] = None) -> str:
        uri = f'mongodb://'
        if self['db_mongo_security_authorization']:
            if not username:
                raise ValueError('Username is mandatory')
            if not password:
                raise ValueError('Password is mandatory')
            uri += f"{username}:{password}@"
        uri += f"{self['db_mongo_hostname']}:{self['db_mongo_port']}"
        if database_name:
            uri += '/' + database_name
        return uri

    def _parameter_postgresql_db_uri(self, username: Optional[str] = None, password: Optional[str] = None, database_name: Optional[str] = None) -> str:
        uri = f'postgresql://'
        username = username or self['db_user']
        password = password or self['db_password']
        uri += f"{username}:{password}@"
        if database_name:
            uri += '/' + database_name
        return uri

    def _parameter_is_debug(self) -> bool:
        return self['log_level'] == LoggerType.DEBUG.value

    def read_parameter(self, name: str, *args, **kwargs) -> Any:
        method_name = '_parameter_' + name
        if not has_method(self, method_name):
            raise AttributeError(f'Parameter "{name}" not found')
        return call_method(self, method_name, *args, **kwargs)

    def add(self, key: str, default_value: Any, ValueType: Optional[Type[Any]] = None, store: bool = False):
        self.setdefault(key, default_value)
        value = self[key]
        if value and ValueType and not isinstance(value, ValueType):
            raise ValueError(f'Inccorect configuration value for parameter "{key}"')
        if store:
            self.stored.append(key)

    @classmethod
    def show_helper(cls):
        return any(arg in ['-h', '--help'] for arg in sys.argv)

    def save_configuration(self):
        values = {k: i for k, i in self.items() if k in self.stored}
        location = default_configuration()
        if location.exists():
            with open(location, 'r+') as file:
                content = json.loads(file.read())
                content.update(values)
                file.seek(0)
                file.write(json.dumps(content))
        else:
            with open(location, 'w') as file:
                file.write(json.dumps(values))


def parse_arguments() -> 'ArgumentParser':
    """Parse system arguments and initiate ERP arguments."""
    # Define argument parser
    parser = argparse.ArgumentParser(prog='MONSTER', description='All in one ERP')
    parser.add_argument(
        '-m', '--mode', dest='mode', type=str, default=Mode.STAGING.value,
        help='ERP mode, choose one of the following options: staging | production'
    )
    parser.add_argument(
        '-c', '--configuration', type=str, dest='configuration',
        help='Path to ERP configuration file in JSON format'
    )
    # Parse arguments and handle help request
    parsed_arguments = parser.parse_args(sys.argv[1:])
    if ArgumentParser.show_helper():
        parser.print_help()
        return ArgumentParser(Mode.STAGING, {})
    else:
        # Load configuration from JSON file if specified
        configuration = {}
        if parsed_arguments.configuration:
            try:
                with open(parsed_arguments.configuration, 'r') as configuration_file:
                    configuration = json.loads(configuration_file.read())
            except Exception as error:
                logging.error(f"Error loading configuration file: {error}")
        location = default_configuration()
        try:
            with location.open('rb') as file:
                content = json.loads(file.read())
                for key, value in content.items():
                    configuration.setdefault(key, value)
        except json.decoder.JSONDecodeError:
            os.remove(location)
        except FileNotFoundError:
            pass
        return ArgumentParser(parsed_arguments.mode, configuration)
