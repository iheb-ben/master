import copy
from typing import Any, Dict, Optional
from werkzeug.local import LocalStack, LocalProxy
from master.core.database import PUBLIC_USER_ID
from master.core.database.cursor import Cursor

_request_stack = LocalStack()
request = LocalProxy(lambda: _request_stack.top)
Context = Dict[str, Any]


class Environment:
    __slots__ = ('registry', 'cursor', 'context', '_sudo', '_uid', '_registry_store')

    def __init__(self, cursor: Cursor, registry: Any, context: Optional[Context] = None, sudo: bool = False, uid: Optional[int] = None):
        self.registry = registry
        self.cursor = cursor
        self.context = context or {}
        self._sudo = sudo
        self._uid = uid or PUBLIC_USER_ID
        self._registry_store = []

    @staticmethod
    def push_request(new_request):
        _request_stack.push(new_request)

    @property
    def user(self):
        return self.sudo()['res.users'].browse(self._uid)

    def with_context(self, **kwargs):
        for key, item in copy.deepcopy(self.context).items():
            kwargs.setdefault(key, item)
        return self.__class__(self.cursor, self.registry, kwargs, self._sudo, self._uid)

    def sudo(self):
        return self.__class__(self.cursor, self.registry, self.context, True, self._uid)

    def is_sudo(self):
        return self._sudo

    def __getitem__(self, item):
        return self.registry[item](self)

    def flush(self):
        while self._registry_store:
            self.cursor.execute(self._registry_store.pop())
