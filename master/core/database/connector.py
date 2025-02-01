import queue
import psycopg2
import threading
import atexit
from contextlib import contextmanager
from psycopg2 import extras
from .cursor import Cursor
from ..tools.config import environ


class PoolManager:
    def __init__(self, minconn, maxconn, **kwargs):
        """
        Initialize the connection pool.

        :param minconn: Minimum number of connections in the pool.
        :param maxconn: Maximum number of connections in the pool.
        :param kwargs: PostgreSQL's connection parameters (e.g., dbname, user, password, host, port).
        """
        self._minconn = minconn
        self._maxconn = maxconn
        self._kwargs = kwargs
        self._pool = queue.Queue(maxconn)  # Thread-safe queue for connection pooling
        self._lock = threading.Lock()  # Lock for thread-safe operations
        self._active_connections = set()  # Track active connections
        self._initialize_pool()  # Initialize the pool with minimum connections
        atexit.register(self.shutdown)  # Register shutdown hook

    def _connect(self, **kwargs):
        for param, value in self._kwargs.items():
            kwargs.setdefault(param, value)
        return psycopg2.connect(**kwargs)

    def _initialize_pool(self):
        """Initialize the pool with the minimum number of connections."""
        for _ in range(self._minconn):
            self._pool.put(self._connect())

    def get_connection(self, timeout=5):
        """
        Get a connection from the pool.

        :param timeout: Timeout in seconds to wait for a connection.
        :return: A PostgreSQL connection object.
        :raises RuntimeError: If the pool is exhausted or a timeout occurs.
        """
        try:
            with self._lock:
                if not self._pool.empty():
                    conn = self._pool.get(timeout=timeout)
                elif len(self._active_connections) < self._maxconn:
                    conn = self._connect()
                else:
                    raise RuntimeError("Connection pool exhausted")
                self._active_connections.add(conn)
            return conn
        except queue.Empty:
            raise RuntimeError("Timeout while waiting for a connection")

    def release_connection(self, conn):
        """
        Release a connection back to the pool.

        :param conn: A PostgreSQL connection object.
        """
        with self._lock:
            self._active_connections.discard(conn)
            self._pool.put(conn)

    def shutdown(self):
        """Close all connections in the pool."""
        with self._lock:
            while not self._pool.empty():
                conn = self._pool.get()
                conn.close()
            for conn in self._active_connections:
                conn.close()

    @contextmanager
    def get_cursor(self, autocommit: bool = True) -> Cursor:
        """
        Get a cursor with optional savepoint support.

        :yield: A PostgreSQL cursor object.
        """
        conn = self.get_connection()
        conn.autocommit = autocommit
        cursor = conn.cursor(cursor_factory=extras.DictCursor)
        try:
            yield Cursor(cursor)
        finally:
            cursor.close()
            self.release_connection(conn)


def main(with_db: bool = False):
    kwargs = dict(
        minconn=with_db and environ['DB_MIN_CONN'] or 1,  # Minimum connections in the pool
        maxconn=with_db and environ['DB_MAX_CONN'] or 1,  # Maximum connections in the pool
        user=environ['PG_USER'],
        password=environ['PG_PASSWORD'],
        host=environ['PG_HOST'],
        port=environ['PG_PORT'],
    )
    if with_db:
        kwargs['dbname'] = environ['PG_NAME']
    return PoolManager(**kwargs)
