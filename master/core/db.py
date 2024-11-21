from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Optional, Dict, Generator, List, Any, Tuple
from pymongo import MongoClient
from pymongo.errors import PyMongoError
import psycopg2
from psycopg2 import sql
from master.config.logging import get_logger
from master.config.parser import arguments
from master.core.api import Class
from master.exceptions.db import DatabaseAccessError, DatabaseSessionError, DatabaseRoleError

ROLE_COLLECTION_NAME = "user_roles"  # Collection for storing user roles in MongoDB
ROLE_TABLE_NAME = "user_roles"  # Table for storing user roles in PostgreSQL
_logger = get_logger(__name__)


class Manager(ABC):
    @abstractmethod
    def admin_connection(self, *args, **kwargs) -> 'Any':
        """Returns a connection with administrative privileges."""
        pass

    @abstractmethod
    def create_role(self, *args, **kwargs) -> None:
        """Assigns a role to a specified user."""
        pass

    @abstractmethod
    def get_role(self, *args, **kwargs) -> 'Any':
        """Fetches the role of a specified user."""
        pass

    @abstractmethod
    def create_connection(self, *args, **kwargs) -> 'Any':
        """Creates a new connection if permissions are met."""
        pass

    @abstractmethod
    def close_connection(self, *args, **kwargs) -> None:
        """Closes an existing connection for a specified user."""
        pass

    @contextmanager
    @abstractmethod
    def transaction(self, *args, **kwargs) -> 'Generator[Any]':
        """Executes a transaction block within a context manager."""
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


class PostgresManager(Class, Manager):
    __meta_path__ = 'master.core.PostgresManager'
    __slots__ = ('database_name', 'connections', 'required')

    def __init__(self, database_name: Optional[str] = None):
        self.database_name: Optional[str] = database_name
        self.connections: Dict[str, psycopg2.connection] = {}
        self.required: List[psycopg2.connection] = []

    def establish_connection(self, username: str, password: str) -> 'psycopg2.connection':
        """Establishes and returns a PostgreSQL connection for a specific user."""
        try:
            if username in self.connections:
                return self.connections[username]
            self.connections[username] = connection = psycopg2.connect(
                host=arguments.configuration['db_hostname'],
                port=arguments.configuration['db_port'],
                password=password,
                user=username,
                dbname=self.database_name)
            return connection
        except psycopg2.Error as e:
            _logger.error(f"Error connecting to PostgreSQL: {e}")
            raise DatabaseSessionError("Could not establish a database connection.")

    def admin_connection(self) -> 'psycopg2.connection':
        """Internal method to return a connection for role management."""
        admin_username = arguments.configuration['db_user']
        if admin_username in self.connections:
            return self.connections[admin_username]
        connection = self.establish_connection(admin_username, arguments.configuration['db_password'])
        self.required.append(connection)
        return connection

    def create_role(self, admin_user_id: str, target_user_id: str, role: str) -> None:
        """Allows an admin to assign a role to a user."""
        if not self.is_admin(admin_user_id):
            raise DatabaseAccessError("Only admins can create roles.")

        connection = self.admin_connection()
        cursor = connection.cursor()
        try:
            query = sql.SQL("INSERT INTO {table} (user_id, role) VALUES (%s, %s) ON CONFLICT (user_id) DO UPDATE SET role = %s").format(
                table=sql.Identifier(ROLE_TABLE_NAME))
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
            query = sql.SQL("SELECT role FROM {table} WHERE user_id = %s").format(
                table=sql.Identifier(ROLE_TABLE_NAME))
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

    def close_connection(self, user_id: str) -> None:
        """Closes a user's connection."""
        if user_id in self.connections:
            if self.connections[user_id] in self.required:
                _logger.warning(f"Cannot close required connection {user_id}")
            else:
                self.connections[user_id].close()
                del self.connections[user_id]
                _logger.info(f"Connection closed for user {user_id}")
        else:
            _logger.info(f"No connection found for user {user_id}")

    @contextmanager
    def transaction(self, user_id: str) -> 'Generator[psycopg2.cursor, None, None]':
        """Executes a transaction block if the user has a connection."""
        if user_id not in self.connections:
            raise DatabaseSessionError(f"No connection found for user {user_id}")

        connection = self.connections[user_id]
        cursor = connection.cursor()

        try:
            yield cursor
            connection.commit()
        except Exception as e:
            connection.rollback()
            _logger.error(f"Transaction for user {user_id} failed: {e}")
            raise e
        finally:
            cursor.close()

    @classmethod
    def check_database_exists(cls, database_name: str) -> bool:
        """Checks if a PostgreSQL database exists by querying pg_database."""
        try:
            manager = cls()
            with manager.admin_connection().cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (database_name,))
                return cursor.fetchone() is not None
        except (psycopg2.Error, DatabaseSessionError):
            return False

    @classmethod
    def create_database(cls, database_name: str) -> None:
        """Creates a new PostgreSQL database with the given name."""
        manager = cls()
        connection = manager.admin_connection()
        connection.set_session(autocommit=True)
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
        except psycopg2.errors.DuplicateDatabase:
            pass

    def __del__(self):
        for connection in self.connections.values():
            connection.close()


class MongoDBManager(Class, Manager):
    __meta_path__ = 'master.core.MongoDBManager'
    __slots__ = ('database_name', 'connections', 'required')

    DEFAULT_COLLECTION_NAME = 'documents'

    def __init__(self, database_name: Optional[str] = None):
        self.database_name: Optional[str] = database_name
        self.connections: Dict[str, MongoClient] = {}
        self.required: List[MongoClient] = []

    def establish_connection(self, username: str, password: str) -> MongoClient:
        """Establishes and returns a MongoDB connection for a specific user."""
        try:
            if username in self.connections:
                return self.connections[username]
            connection_string = arguments.read_parameter('mongo_db_uri', username, password, self.database_name)
            self.connections[username] = connection = MongoClient(connection_string)
            return connection
        except PyMongoError as e:
            _logger.error(f"Error connecting to MongoDB: {e}")
            raise DatabaseSessionError("Could not establish a database connection.")

    def admin_connection(self) -> MongoClient:
        """Returns an admin connection for role management."""
        admin_username = arguments.configuration['db_mongo_user']
        if admin_username in self.connections:
            return self.connections[admin_username]
        connection = self.establish_connection(admin_username, arguments.configuration['db_mongo_password'])
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
            roles_collection.update_one(
                {'user_id': target_user_id},
                {'$set': {'role': role}},
                upsert=True
            )
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

    def close_connection(self, user_id: str) -> None:
        """Closes a user's connection."""
        if user_id in self.connections:
            if self.connections[user_id] in self.required:
                _logger.warning(f"Cannot close required connection {user_id}")
            else:
                self.connections[user_id].close()
                del self.connections[user_id]
                _logger.info(f"Connection closed for user {user_id}")
        else:
            _logger.info(f"No connection found for user {user_id}")

    @contextmanager
    def transaction(self, user_id: str) -> Generator[MongoClient, None, None]:
        """Executes a transaction block if the user has a connection."""
        if user_id not in self.connections:
            raise DatabaseSessionError(f"No connection found for user {user_id}")

        connection = self.connections[user_id]
        db = connection[self.database_name]
        session = connection.start_session()

        try:
            with session.start_transaction():
                yield db
                session.commit_transaction()
        except PyMongoError as e:
            session.abort_transaction()
            _logger.error(f"Transaction for user {user_id} failed: {e}")
            raise e
        finally:
            session.end_session()

    @classmethod
    def check_database_exists(cls, database_name: str) -> bool:
        """Checks if a MongoDB database exists."""
        try:
            manager = cls()
            client = manager.admin_connection()
            database_list = client.list_database_names()
            return database_name in database_list
        except (PyMongoError, DatabaseSessionError):
            return False

    @classmethod
    def create_database(cls, database_name: str) -> None:
        """Creates a new MongoDB database with the given name."""
        manager = cls()
        client = manager.admin_connection()
        # In MongoDB, databases are created lazily. Accessing a collection creates the DB.
        client[database_name].create_collection(cls.DEFAULT_COLLECTION_NAME)

    def __del__(self):
        for connection in self.connections.values():
            connection.close()


def main():
    default_db_name: str = arguments.read_parameter('default_db_name')
    if not PostgresManager.check_database_exists(default_db_name):
        PostgresManager.create_database(default_db_name)
        _logger.debug(f'Database "{default_db_name}" created successfully in PostgreSQL.')
    if arguments.configuration['db_mongo'] and not MongoDBManager.check_database_exists(default_db_name):
        MongoDBManager.create_database(default_db_name)
        _logger.debug(f'Database "{default_db_name}" created successfully in MongoDB.')
