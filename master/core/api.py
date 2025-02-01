from typing import Any, Dict
from werkzeug.local import LocalStack, LocalProxy
from master.core.database.cursor import Cursor

_request_stack = LocalStack()
request = LocalProxy(lambda: _request_stack.top)
Context = Dict[str, Any]


class Environment:
    def __init__(self, cursor: Cursor, registry: Any, context: Context):
        self.registry = registry
        self.cursor = cursor
        self.context = context
        self._savepoint = cursor.current_savepoint

    @staticmethod
    def push_request(new_request):
        _request_stack.push(new_request)

    def __getitem__(self, item):
        return self.registry[item]

    def flush(self):
        self.cursor.release_all_savepoints(self._savepoint)
