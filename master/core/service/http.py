from collections import defaultdict
from contextlib import contextmanager
from typing import Any, Type, Optional, List, Dict, Callable, Generator, Union, Iterable
from werkzeug.routing import BaseConverter as _BaseConverter, Rule
from werkzeug.wrappers import Request as _Request, Response as _Response
from master.core.api import Environment, request, Component
from master.core.tools import filter_class, simplify_class_name

HTTP_METHODS = ['GET', 'PUT', 'POST', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS', 'TRACE']


class Response(_Response):
    def __init__(self, *args, **kwargs):
        self.template = kwargs.pop('template', None)
        self.context = kwargs.pop('context', {})
        super().__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
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

    def __init__(self, application: Callable, httprequest: _Request):
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
        methods: Optional[List[str]] = None,
    ):
        self.auth = auth
        self.func_name = func_name
        self.rollback = rollback
        self.sitemap = sitemap
        self.content = content
        self.methods = methods

    def wrap(self, func: Callable, **kwargs):
        kwargs.setdefault('auth', self.auth)
        kwargs.setdefault('rollback', self.rollback)
        kwargs.setdefault('content', self.content)
        kwargs.setdefault('methods', self.methods)
        kwargs['sitemap'] = self.sitemap
        return self.__class__(func_name=func, **kwargs)

    def as_rule(self, url: str):
        return Rule(string=url, endpoint=self, methods=self.methods)

    def __repr__(self):
        func_name = self.func_name
        if not isinstance(func_name, str):
            func_name = func_name.__name__
        required = self.auth and '*' or ''
        methods = self.methods or HTTP_METHODS
        return f'{func_name}{required} {methods} [CONTENT: {self.content}] (ID: {id(self)})'


def build_controller_class(installed: List[str]):
    current_list = []
    for addon in installed:
        current_list.extend(Controller.__children__[addon])
    if not current_list:
        return Controller
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


# noinspection PyMethodParameters,PyPropertyDefinition,PyMethodMayBeStatic
class Controller(Component):
    __children__: Dict[str, List[Type]] = defaultdict(list)
    __endpoints__: Dict[str, Dict[str, Endpoint]] = defaultdict(dict)
    __converters__: Dict[str, Dict[str, List[Type]]] = defaultdict(dict)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        current_addon: Optional[str] = cls.__addon__
        if not current_addon and cls.__name__ != '_Controller':
            raise ValueError('Current controller is not part of the master addons package')
        if current_addon:
            Controller.__children__[current_addon].append(cls)

    def __init__(
        self,
        application: Any = None,
        endpoints: Optional[Dict[str, Endpoint]] = None,
        converters: Optional[Dict[str, Converter]] = None,
    ):
        self._compiled_endpoints: Optional[Dict[str, Endpoint]] = endpoints or {}
        self._compiled_converters: Optional[Dict[str, Converter]] = converters or {}
        if application is not None:
            for installed_module in reversed(application.installed):
                for url, module_endpoint in Controller.__endpoints__.items():
                    if url in self._compiled_endpoints:
                        continue
                    for module, endpoint in module_endpoint.items():
                        if module != installed_module:
                            continue
                        if isinstance(endpoint.func_name, str):
                            if not hasattr(self, endpoint.func_name) or endpoint.func_name.startswith('_'):
                                continue
                            attach_endpoint = endpoint.wrap(self.__getattribute__(endpoint.func_name))
                        else:
                            attach_endpoint = endpoint
                        self._compiled_endpoints.setdefault(url, attach_endpoint)
                        break

    def get_rules(self):
        return [endpoint.as_rule(url=url) for url, endpoint in self._compiled_endpoints.items()]

    def __call__(self):
        raise NotImplemented()


def route(
    *urls,
    auth: bool = False,
    rollback: bool = True,
    sitemap: bool = True,
    content: Optional[str] = None,
    methods: Optional[List[str]] = None,
):
    if methods is not None and not isinstance(methods, Iterable):
        methods = [methods]

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
                methods=methods and [v.upper() for v in methods if v and not v.isspace()] or None,
            )
        return func
    return _
