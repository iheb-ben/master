import datetime
import logging
import threading
import uuid
from abc import abstractmethod
from typing import Optional, Dict, Generator, List, Any, Generic, AnyStr
from pymongo import MongoClient
from pymongo.errors import PyMongoError
import psycopg2
import psycopg2.extensions
import psycopg2.errors
from psycopg2 import sql

from master.api import check_lock
from master.core import arguments
from master.core.registry import BaseClass
from master.exceptions import DatabaseAccessError, DatabaseSessionError, DatabaseRoleError

ROLE_COLLECTION_NAME = "user_roles"  # Collection for storing user roles in MongoDB
ROLE_TABLE_NAME = "user_roles"  # Table for storing user roles in PostgreSQL
_logger = logging.getLogger(__name__)


class Manager(Generic[AnyStr]):
    @abstractmethod
    def admin_connection(self, *args, **kwargs) -> Any:
        """Returns a connection with administrative privileges."""
        pass

    @abstractmethod
    def create_role(self, *args, **kwargs) -> None:
        """Assigns a role to a specified user."""
        pass

    @abstractmethod
    def get_role(self, *args, **kwargs) -> Any:
        """Fetches the role of a specified user."""
        pass

    @abstractmethod
    def create_connection(self, *args, **kwargs) -> Any:
        """Creates a new connection if permissions are met."""
        pass

    @abstractmethod
    def close_connection(self, *args, **kwargs) -> None:
        """Closes an existing connection for a specified user."""
        pass

    @abstractmethod
    def close(self, *args, **kwargs) -> None:
        """Closes all existing connection."""
        pass

    @classmethod
    @abstractmethod
    def check_database_exists(cls, *args, **kwargs) -> bool:
        """Checks if a specific database exists."""
        pass

    @classmethod
    @abstractmethod
    def create_database(cls, *args, **kwargs) -> None:
        """Creates a new database with the given name."""
        pass


postgres_admin_connection: Optional[psycopg2.extensions.connection] = None


class PostgresManager(BaseClass, Manager):
    __slots__ = ('database_name', 'connections', 'required', '_lock')

    def __init__(self, database_name: Optional[str] = None):
        self.database_name: Optional[str] = database_name
        self.connections: Dict[str, psycopg2.extensions.connection] = {}
        self.required: List[psycopg2.extensions.connection] = []
        if postgres_admin_connection:
            self.connections[arguments['db_user']] = postgres_admin_connection
            self.required.append(postgres_admin_connection)
        self._lock = threading.RLock()

    @check_lock
    def establish_connection(self, username: str, password: str) -> psycopg2.extensions.connection:
        """Establishes and returns a PostgreSQL connection for a specific user."""
        try:
            if username in self.connections:
                return self.connections[username]
            self.connections[username] = connection = psycopg2.connect(
                host=arguments['db_host'],
                port=arguments['db_port'],
                password=password,
                user=username,
                dbname=self.database_name)
            return connection
        except psycopg2.Error as e:
            _logger.error(f"Error connecting to PostgreSQL: {e}")
            raise DatabaseSessionError("Could not establish a database connection.")

    def admin_connection(self) -> psycopg2.extensions.connection:
        """Internal method to return a connection for role management."""
        global postgres_admin_connection
        admin_username = arguments['db_user']
        if admin_username in self.connections:
            return self.connections[admin_username]
        connection = self.establish_connection(admin_username, arguments['db_password'])
        if self.database_name:
            postgres_admin_connection = connection
            self.required.append(connection)
        else:
            connection.autocommit = True
        return connection

    def create_role(self, admin_user_id: str, target_user_id: str, role: str) -> None:
        """Allows an admin to assign a role to a user."""
        if not self.is_admin(admin_user_id):
            raise DatabaseAccessError("Only admins can create roles.")
        connection = self.admin_connection()
        cursor = connection.cursor()
        try:
            query = sql.SQL("INSERT INTO {table} (user_id, role) VALUES (%s, %s) ON CONFLICT (user_id) DO UPDATE SET role = %s").format(table=sql.Identifier(ROLE_TABLE_NAME))
            cursor.execute(query, (target_user_id, role, role))
            connection.commit()
            _logger.info(f"Role '{role}' assigned to user {target_user_id} by admin {admin_user_id}")
        except Exception as e:
            connection.rollback()
            _logger.error(f"Failed to assign role: {e}", exc_info=True)
            raise DatabaseRoleError(str(e))
        finally:
            cursor.close()

    def get_role(self, user_id: str) -> Optional[str]:
        """Fetches the role of a user."""
        connection = self.admin_connection()
        cursor = connection.cursor()
        try:
            query = sql.SQL("SELECT role FROM {table} WHERE user_id = %s").format(table=sql.Identifier(ROLE_TABLE_NAME))
            cursor.execute(query, (user_id,))
            result = cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            _logger.error(f"Failed to get role: {e}", exc_info=True)
            raise DatabaseRoleError(str(e))
        finally:
            cursor.close()

    def is_admin(self, user_id: str) -> bool:
        """Checks if a user has an admin role."""
        return self.get_role(user_id) == "admin"

    def create_connection(self, user_id: str, password: str) -> None:
        """Creates a new PostgreSQL connection if the user is an admin."""
        if not self.is_admin(user_id):
            raise DatabaseAccessError("Only admins can create connections.")
        if user_id not in self.connections:
            self.connections[user_id] = self.establish_connection(user_id, password)
            _logger.info(f"Connection created for admin user {user_id}")
        else:
            _logger.info(f"Connection for user {user_id} already exists")

    @check_lock
    def close_connection(self, user_id: str, force: bool = False) -> None:
        """Closes a user's connection."""
        if user_id in self.connections:
            if self.connections[user_id] in self.required and not force:
                _logger.warning(f"Cannot close required connection {user_id}")
            else:
                self.connections[user_id].close()
                del self.connections[user_id]
                _logger.info(f"Connection closed for user {user_id}")
        else:
            _logger.info(f"No connection found for user {user_id}")

    @classmethod
    def check_database_exists(cls, database_name: str) -> bool:
        """Checks if a PostgreSQL database exists by querying pg_database."""
        manager = cls()
        connection = manager.admin_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql.SQL('SELECT 1 FROM pg_database WHERE datname = %s'), (database_name,))
            result = cursor.fetchone() is not None
        manager.close()
        return result

    @classmethod
    def create_database(cls, database_name: str) -> None:
        """Creates a new PostgreSQL database with the given name."""
        manager = cls()
        connection = manager.admin_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
        except psycopg2.errors.DuplicateDatabase:
            connection.rollback()
        finally:
            manager.close()

    @check_lock
    def close(self, force: bool = False):
        for user_id in set(self.connections.keys()):
            self.close_connection(user_id=user_id, force=force)


def _mongo_db_uri(username: Optional[str] = None, password: Optional[str] = None, database_name: Optional[str] = None) -> str:
    uri = f'mongodb://'
    if arguments['db_mongo_security_authorization']:
        if not username:
            raise ValueError('Username is mandatory')
        if not password:
            raise ValueError('Password is mandatory')
        uri += f"{username}:{password}@"
    uri += f"{arguments['db_mongo_host']}:{self['db_mongo_port']}"
    if database_name:
        uri += '/' + database_name
    return uri


mongo_admin_connection: Optional[MongoClient] = None


class MongoDBManager(BaseClass, Manager):
    __slots__ = ('database_name', 'connections', 'required', '_lock')

    DEFAULT_COLLECTION_NAME = 'documents'

    def __init__(self, database_name: Optional[str] = None):
        self.database_name: Optional[str] = database_name
        self.connections: Dict[str, MongoClient] = {}
        self.required: List[MongoClient] = []
        if mongo_admin_connection:
            self.connections[arguments['db_mongo_user']] = mongo_admin_connection
            self.required.append(mongo_admin_connection)
        self._lock = threading.RLock()

    @check_lock
    def establish_connection(self, username: str, password: str) -> MongoClient:
        """Establishes and returns a MongoDB connection for a specific user."""
        try:
            if username in self.connections:
                return self.connections[username]
            connection_string = _mongo_db_uri(username, password, self.database_name)
            self.connections[username] = connection = MongoClient(connection_string)
            return connection
        except PyMongoError as e:
            _logger.error(f"Error connecting to MongoDB: {e}")
            raise DatabaseSessionError("Could not establish a database connection.")

    def admin_connection(self) -> MongoClient:
        """Returns an admin connection for role management."""
        global mongo_admin_connection
        admin_username = arguments['db_mongo_user']
        if admin_username in self.connections:
            return self.connections[admin_username]
        connection = self.establish_connection(admin_username, arguments['db_mongo_password'])
        if self.database_name:
            mongo_admin_connection = connection
            self.required.append(connection)
        return connection

    def create_role(self, admin_user_id: str, target_user_id: str, role: str) -> None:
        """Assigns a role to a user if the requester is an admin."""
        if not self.is_admin(admin_user_id):
            raise DatabaseAccessError("Only admins can create roles.")
        connection = self.admin_connection()
        db = connection[self.database_name]
        roles_collection = db[ROLE_COLLECTION_NAME]
        try:
            roles_collection.update_one({'user_id': target_user_id}, {'$set': {'role': role}}, upsert=True)
            _logger.info(f"Role '{role}' assigned to user {target_user_id} by admin {admin_user_id}")
        except PyMongoError as e:
            _logger.error(f"Failed to assign role: {e}", exc_info=True)
            raise DatabaseRoleError(str(e))

    def get_role(self, user_id: str) -> Optional[str]:
        """Fetches the role of a user."""
        connection = self.admin_connection()
        db = connection[self.database_name]
        roles_collection = db[ROLE_COLLECTION_NAME]
        try:
            role_data = roles_collection.find_one({'user_id': user_id})
            return role_data['role'] if role_data else None
        except PyMongoError as e:
            _logger.error(f"Failed to get role: {e}", exc_info=True)
            raise DatabaseRoleError(str(e))

    def is_admin(self, user_id: str) -> bool:
        """Checks if a user has an admin role."""
        return self.get_role(user_id) == "admin"

    def create_connection(self, user_id: str, password: str) -> None:
        """Creates a new MongoDB connection if the user is an admin."""
        if not self.is_admin(user_id):
            raise DatabaseAccessError("Only admins can create connections.")
        if user_id not in self.connections:
            self.connections[user_id] = self.establish_connection(user_id, password)
            _logger.info(f"Connection created for admin user {user_id}")
        else:
            _logger.info(f"Connection for user {user_id} already exists")

    @check_lock
    def close_connection(self, user_id: str, force: bool = False) -> None:
        """Closes a user's connection."""
        if user_id in self.connections:
            if self.connections[user_id] in self.required and not force:
                _logger.warning(f"Cannot close required connection {user_id}")
            else:
                self.connections[user_id].close()
                del self.connections[user_id]
                _logger.info(f"Connection closed for user {user_id}")
        else:
            _logger.info(f"No connection found for user {user_id}")

    @classmethod
    def check_database_exists(cls, database_name: str) -> bool:
        """Checks if a MongoDB database exists."""
        manager = cls()
        client = manager.admin_connection()
        result = False
        try:
            database_list = client.list_database_names()
            result = database_name in database_list
        except PyMongoError:
            pass
        finally:
            manager.close()
        return result

    @classmethod
    def create_database(cls, database_name: str) -> None:
        """Creates a new MongoDB database with the given name."""
        manager = cls()
        client = manager.admin_connection()
        # In MongoDB, databases are created lazily. Accessing a collection creates the DB.
        client[database_name].create_collection(cls.DEFAULT_COLLECTION_NAME)
        manager.close()

    @check_lock
    def close(self, force: bool = False):
        for user_id in set(self.connections.keys()):
            self.close_connection(user_id=user_id, force=force)


def initialization():
    """
    Main entry point for initialization databases.
    """
    default_db_name: str = arguments['db_name']
    if not PostgresManager.check_database_exists(default_db_name):
        PostgresManager.create_database(default_db_name)
        _logger.debug(f'Database "{default_db_name}" created successfully in PostgreSQL.')
    if arguments['db_mongo'] and not MongoDBManager.check_database_exists(default_db_name):
        MongoDBManager.create_database(default_db_name)
        _logger.debug(f'Database "{default_db_name}" created successfully in MongoDB.')


def load_installed_modules() -> List[str]:
    """
    Retrieves the set of default installed modules from the database.
    """
    required_modules = []
    manager = PostgresManager(arguments['db_name'])
    connection = manager.admin_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT DISTINCT key, sequence FROM module_module WHERE state IN ('installed', 'to_update') ORDER BY sequence ASC;")
            _logger.debug('Retrieved installed modules from the database.')
            required_modules = [row[0] for row in cursor.fetchall()]
    except psycopg2.errors.UndefinedTable:
        connection.rollback()
        _logger.debug('Could not retrieve default modules from database.')
    finally:
        manager.close()
    return required_modules


def translate(source: str):
    if postgres_admin_connection:
        savepoint_name = None
        with postgres_admin_connection.cursor() as cursor:
            try:
                _savepoint_name = 'savepoint_' + uuid.uuid4().hex + '_TR'
                cursor.execute(f'SAVEPOINT "{_savepoint_name}"')
                savepoint_name = _savepoint_name
                query = sql.SQL('SELECT translation FROM system_translations WHERE source = %s AND language = %s LIMIT 1')
                language = 'en'
                from master import request
                if request:
                    language = request.headers.get('language', 'en')
                cursor.execute(query, (source, language))
                translation = cursor.fetchone()
                cursor.execute(f'RELEASE SAVEPOINT "{savepoint_name}"')
                if translation:
                    return translation[0]
            except psycopg2.errors.UndefinedTable:
                if savepoint_name:
                    cursor.execute(f'ROLLBACK TO SAVEPOINT "{savepoint_name}"')
    return source
