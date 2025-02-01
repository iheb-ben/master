from typing import Tuple, List, Union, Optional, Generator, Any
from uuid import uuid4
from contextlib import contextmanager
# noinspection PyPep8Naming,PyProtectedMember
from psycopg2._psycopg import cursor as _BaseCursor
from psycopg2.sql import SQL
from psycopg2 import Error as _BaseCursorError


class Cursor:
    def __init__(self, cursor: _BaseCursor):
        self._cursor = cursor
        self._savepoints: List[str] = []
        self._begin = False

    def create_savepoint(self, name: Optional[str] = None) -> str:
        if not self._begin:
            self.execute(sql='BEGIN')
            self._begin = True
        name = name or str(uuid4())
        self._savepoints.append(name)
        self.execute(sql=f'SAVEPOINT "{name}"')
        return name

    def rollback_savepoint(self, name: Optional[str] = None):
        name = name or self.current_savepoint
        if name in self._savepoints:
            self.execute(sql=f'ROLLBACK TO SAVEPOINT "{name}"')

    def release_savepoint(self, name: Optional[str] = None):
        name = name or self.current_savepoint
        if name in self._savepoints:
            self.execute(sql=f'RELEASE SAVEPOINT "{name}"')
            self._savepoints.remove(name)
        if self._begin and not self._savepoints:
            self.execute(sql='END')

    @contextmanager
    def with_savepoint(self) -> Generator[str, None, None]:
        name = self.create_savepoint()
        try:
            yield name
        except Exception:
            self.rollback_savepoint(name)
            raise
        finally:
            self.release_savepoint(name)

    @property
    def current_savepoint(self):
        return self._savepoints[-1] if self._savepoints else None

    @property
    def pg_cursor(self):
        return self._cursor

    def execute(
            self,
            sql: Union[SQL, str],
            variables: Optional[Union[Tuple, List[Tuple]]] = None,
            fetch_type: Optional[str] = None,
            limit: Optional[int] = None,
            raise_error: bool = True,
            default: Any = None,
    ):
        result = None
        try:
            if variables:
                if isinstance(variables, tuple):
                    self._cursor.execute(sql, variables)
                elif isinstance(variables, list):
                    self._cursor.executemany(sql, variables)
                else:
                    self._cursor.execute(sql, (variables,))
            else:
                self._cursor.execute(sql)
        except _BaseCursorError:
            if raise_error:
                raise
            else:
                return default
        if fetch_type or limit:
            result = self.fetch(fetch_type=fetch_type, limit=limit)
        return result or default

    def fetch(self, fetch_type: str = 'all', limit: int = 0):
        fetch_type = fetch_type or 'all'
        limit = limit or 0
        if limit > 0:
            fetch_type = 'many'
        elif limit == 1:
            fetch_type = 'one'
        else:
            fetch_type = fetch_type.lower().strip()
        method = getattr(self._cursor, f'fetch{fetch_type}')
        if not method:
            raise RuntimeError(f'Fetch type {fetch_type} not supported')
        if fetch_type == 'many':
            return method(limit)
        return method()
