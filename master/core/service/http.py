import json
from collections import defaultdict
from contextlib import contextmanager
from typing import Any, Type, Optional, List, Dict, Callable, Generator, Union
from werkzeug.routing import BaseConverter as _BaseConverter, Rule
from werkzeug.wrappers import Request as _Request, Response as _Response
from master.core.api import Environment, request, Component
from master.core.database.cursor import Cursor
from master.core.tools import filter_class, simplify_class_name


class Response(_Response):
    def __init__(self, *args, **kwargs):
        self.template = kwargs.pop('template', None)
        self.context = kwargs.pop('context', {})
        if self.template:
            kwargs.setdefault('content_type', 'text/html')
        super().__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        if self.template:
            for key, item in request.context.items():
                self.context.setdefault(key, item)
        self.context.setdefault('error', request.error)
        self.context['request'] = request
        if not self.data and self.status_code == 200:
            self.status_code = 204
        return super().__call__(*args, **kwargs)


class Request:
    __slots__ = ('httprequest', 'application', 'env', 'error', 'context', 'rule')

    def __new__(cls, *args, **kwargs):
        if request:
            new_request = request
        else:
            new_request = super().__new__(cls)
            Environment.push_request(new_request)
        return new_request

    def __init__(self, httprequest: _Request, application: Callable):
        self.httprequest = httprequest
        self.application = application
        self.env: Optional[Environment] = None
        self.rule: Optional[Rule] = None
        self.error: Optional[Exception] = None
        self.context: Dict[str, Any] = {}

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
    def __init__(
        self,
        func_name: Optional[Union[str, Callable]] = None,
        auth: bool = False,
        rollback: bool = False,
        sitemap: bool = True,
        content: Optional[str] = None,
    ):
        self.auth = auth
        self.func_name = func_name
        self.rollback = rollback
        self.sitemap = sitemap
        self.content = content

    def wrap(self, func: Callable, **kwargs):
        kwargs.setdefault('auth', self.auth)
        kwargs.setdefault('rollback', self.rollback)
        kwargs.setdefault('content', self.content)
        kwargs['sitemap'] = self.sitemap
        return self.__class__(func_name=func, **kwargs)

    def as_rule(self, url: str):
        return Rule(string=url, endpoint=self)

    def __call__(self, *args, **kwargs):
        if self.rollback:
            with request.env.cursor.with_savepoint():
                response = self.func_name(*args, **kwargs)
        else:
            response = self.func_name(*args, **kwargs)
        response = response or Response(status=200)
        if isinstance(response, dict):
            response = json.dumps(response)
        if not isinstance(response, _Response):
            status = 200
            if isinstance(response, tuple):
                response, status = response
            if isinstance(response, dict):
                response = json.dumps(response)
            response = Response(response=response, status=status)
        if self.content and response.content_type.startswith('text/plain'):
            response.content_type = self.content
        return response


def build_controller_class(installed: List[str]):
    current_list = []
    for addon in installed:
        current_list.extend(Controller.__children__[addon])
    if not current_list:
        return None
    controller_classes = filter_class(current_list)
    if len(controller_classes) == 1:
        return controller_classes[0]
    else:
        return type('_Controller', tuple(controller_classes), {})


def build_converters_class(installed: List[str]):
    filtered_converters = defaultdict(list)
    for name, module_converters in Controller.__converters__.items():
        for addon in installed:
            filtered_converters[name].extend(module_converters.get(addon, []))
    converters = {}
    for name, elements in filtered_converters.items():
        converter_klass = filter_class(elements)
        if len(converter_klass) == 1:
            converter_klass = converter_klass[0]
        else:
            converter_klass = type('_Converter', tuple(converter_klass), {})
        converters[name] = converter_klass
    return converters


class Converter(Component, _BaseConverter):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # noinspection PyTypeChecker
        current_addon: Optional[str] = cls.__addon__
        if current_addon:
            converter_name = simplify_class_name(cls.__name__)
            if not Controller.__converters__[converter_name].get(current_addon):
                Controller.__converters__[converter_name][current_addon] = [cls]
            else:
                Controller.__converters__[converter_name][current_addon].append(cls)


_compiled_controller: Optional[Type] = None


# noinspection PyMethodParameters,PyPropertyDefinition
class Controller(Component):
    __children__: Dict[str, List[Type]] = defaultdict(list)
    __endpoints__: Dict[str, Dict[str, Endpoint]] = defaultdict(dict)
    __converters__: Dict[str, Dict[str, List[Type]]] = defaultdict(dict)
    __compiled_converters__: Dict[str, Converter] = {}

    @staticmethod
    def compiled(cls):
        globals()['_compiled_controller'] = cls

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # noinspection PyTypeChecker
        current_addon: Optional[str] = cls.__addon__
        if not current_addon and cls.__name__ != '_Controller':
            raise ValueError('Current controller is not part of the master addons package')
        if current_addon:
            cls.__children__[current_addon].append(cls)

    def __new__(cls, *args, **kwargs):
        if cls is Controller and _compiled_controller:
            return _compiled_controller.__new__(_compiled_controller, *args, **kwargs)
        return super().__new__(cls)

    def dispatch(self):
        raise NotImplemented()


def route(
    *urls,
    auth: bool = False,
    rollback: bool = True,
    sitemap: bool = True,
    content: Optional[str] = 'text/html',
):
    def _(func: Callable):
        if not func.__module__.startswith('master.addons.'):
            raise ValueError('Current function is not part of the master addons package')
        module = func.__module__.split('.')[2]
        if not module:
            raise RuntimeError('Routing issue, module name not found')
        for url in urls:
            Controller.__endpoints__[url][module] = Endpoint(
                func_name=func.__name__,
                auth=auth,
                rollback=rollback,
                sitemap=sitemap,
                content=content,
            )
        return func
    return _


def json_route(*args, **kwargs):
    kwargs['content'] = 'application/json'
    return route(*args, **kwargs)


def html_route(*args, **kwargs):
    kwargs['content'] = 'text/html'
    return route(*args, **kwargs)
