import copy
from functools import cached_property
from typing import Any, Dict, Optional
from werkzeug.local import LocalStack, LocalProxy
from master.core.database import PUBLIC_USER_ID
from master.core.database.cursor import Cursor
from master.core.tools import is_valid_name

_request_stack = LocalStack()
request = LocalProxy(lambda: _request_stack.top)
Context = Dict[str, Any]


# noinspection PyPropertyDefinition
class Component(object):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not is_valid_name(cls.__name__):
            raise ValueError("""Check if a string adheres to the following rules:\n
1. Can start with _ or an uppercase letter (A-Z).\n
2. Contains only letters (A-Z, a-z).""")

    @classmethod
    @property
    def __addon__(cls):
        if cls.__module__.startswith('master.addons.'):
            return cls.__module__.split('.')[2]
        return None


class Environment:
    __slots__ = ('registry', 'cursor', 'context', '_sudo', '_uid', '_store')

    def __init__(self, cursor: Cursor, registry: Any, context: Optional[Context] = None, sudo: bool = False, uid: Optional[int] = None):
        self.registry = registry
        self.cursor = cursor
        self.context = context or {}
        self._sudo = sudo
        self._uid = uid or PUBLIC_USER_ID
        self._store = []

    @staticmethod
    def push_request(new_request):
        _request_stack.push(new_request)

    @cached_property
    def user(self):
        return self.sudo()['res.users'].browse(self._uid)

    def with_context(self, **kwargs):
        for key, item in copy.deepcopy(self.context).items():
            kwargs.setdefault(key, item)
        return self.__class__(self.cursor, self.registry, kwargs, self._sudo, self._uid)

    def with_user(self, uid: int):
        return self.__class__(self.cursor, self.registry, self.context, self._sudo, uid)

    def sudo(self):
        return self.__class__(self.cursor, self.registry, self.context, True, self._uid)

    def is_sudo(self):
        return self._sudo

    def __getitem__(self, item):
        return self.registry[item](self)

    def flush(self):
        while self._store:
            self.cursor.execute(self._store.pop(0))
