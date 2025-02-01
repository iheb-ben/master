from collections import defaultdict
from contextlib import contextmanager
from typing import Any, Type, Optional, List, Dict, Callable, Generator
from werkzeug.wrappers import Request as _Request
from master.core.api import Environment, request
from master.core.database.cursor import Cursor
from master.core.tools import filter_class, is_valid_name


class Request:
    __slots__ = ('httprequest', 'application', 'env')

    def __new__(cls, *args, **kwargs):
        if request:
            new_request = request
        else:
            new_request = super().__new__(cls)
            Environment.push_request(new_request)
        return new_request

    def __init__(self, httprequest: _Request, application: Any):
        self.httprequest = httprequest
        self.application = application
        self.env: Optional[Environment] = None

    @contextmanager
    def create_environment(self, **kwargs) -> Generator[Environment, None, None]:
        with self.application.pool.get_cursor() as cursor:
            if self.env:
                kwargs.setdefault('context', self.env.context)
                kwargs.setdefault('sudo', self.env.is_sudo())
                kwargs.setdefault('uid', self.env.user.id)
            yield Environment(cursor, self.application.registry, **kwargs)

    def __repr__(self):
        return repr(self.httprequest)


class Endpoint:
    def __init__(self, url: str, auth: bool, module: str):
        self.module = module
        self.auth = auth
        self.url = url


def build_controller_class(installed: List[str]):
    current_list = []
    for addon in installed:
        current_list.extend(Controller.__children__[addon])
    if not current_list:
        return Controller
    return type('MetaController', tuple(filter_class(current_list)), {})


class Controller:
    __children__: Dict[str, List[Type]] = defaultdict(list)
    __object__: Optional[Type] = None
    __endpoints__: Dict[str, List[Endpoint]] = defaultdict(list)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not is_valid_name(cls.__name__):
            raise ValueError('''Check if a string adheres to the following rules:\n
1. Can start with _ or an uppercase letter (A-Z).\n
2. Contains only letters (A-Z, a-z).''')
        if not cls.__module__.startswith('master.addons.') and cls.__name__ != 'MetaController':
            raise ValueError('Current controller is not part of the master addons package')
        if cls.__module__.startswith('master.addons.'):
            cls.__children__[cls.__module__.split('.')[2]].append(cls)

    def __new__(cls, *args, **kwargs):
        return cls.__object__ or super().__new__(cls)


def route(*urls, auth: bool = False):
    def _(func: Callable):
        if not func.__module__.startswith('master.addons.'):
            raise ValueError('Current function is not part of the master addons package')
        module = func.__module__.split('.')[2]
        if not module:
            raise RuntimeError('Routing issue, module name not found')
        for url in urls:
            Controller.__endpoints__[func.__name__].append(Endpoint(
                url=url,
                auth=auth,
                module=module,
            ))
        return func
    return _
