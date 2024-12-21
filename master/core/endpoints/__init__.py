import json
from inspect import Parameter, signature as inspect_signature
from io import BytesIO
from pathlib import Path
from typing import Union, List, Dict, Any, Callable, Optional, Generator, Set, Mapping, Type
from werkzeug.datastructures import MultiDict
from werkzeug.exceptions import UnsupportedMediaType, HTTPException, Unauthorized, Forbidden
from werkzeug.formparser import parse_form_data
from werkzeug.local import Local
from werkzeug.routing import Rule, Map, BaseConverter
from werkzeug.wrappers import Request as _Request, Response as _Response

from master import request
from master.api import lazy_property
from master.core import arguments, signature
from master.core.db import translate
from master.core.git import token
from master.core.parser import PipelineMode
from master.core.registry import BaseClass

from . import converters as system_converters


# noinspection PyMethodMayBeStatic
class Request(BaseClass, _Request):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint: Optional[Endpoint] = None
        self.values_dict: Dict[str, Any] = {}
        setattr(local, 'request', self)

    @lazy_property
    def csrf_token(self) -> Optional[str]:
        values = self.values_dict.copy()
        values.setdefault('csrf_token', self.headers.get('X-CSRFToken', None))
        _csrf_token = values.get('csrf_token')
        return _csrf_token and _csrf_token.strip() or None

    def get_client_ip(self) -> Optional[str]:
        """
        Extract the client's IP address, considering proxies.
        """
        for header_key in ['X-Real-IP', 'X-Forwarded-For']:
            header_value = self.headers.get(header_key)
            if not header_value:
                continue
            for ip in header_value.split(','):
                client_ip = ip and ip.strip() or ''
                if not client_ip:
                    continue
                return client_ip
        return self.remote_addr

    def is_localhost(self) -> bool:
        """
        Check if the IP address is localhost.
        """
        localhost_ips: Set[str] = {'127.0.0.1', '::1'}
        if signature['public_ip']:
            localhost_ips.add(signature['public_ip'])
        return self.get_client_ip() in localhost_ips

    def read_parameters(self) -> Dict[str, Any]:
        """
        Reads and parses request parameters based on the Content-Type.
        Supports JSON, form-encoded, and multipart data.
        """
        if self.method in ('PUT', 'POST', 'PATCH'):
            stream_factory: Callable = lambda: BytesIO(self.data)
            content_type = self.headers.get('Content-Type', '')
            try:
                if not content_type or content_type.startswith('application/json'):
                    return self.json
                elif content_type.startswith('application/x-www-form-urlencoded'):
                    return MultiDict(self.form).to_dict()
                elif content_type.startswith('multipart/form-data'):
                    _, form_data, _ = parse_form_data(environ=self.environ, stream_factory=stream_factory)
                    return MultiDict(form_data).to_dict()
            except UnsupportedMediaType:
                if not content_type:
                    if self.form:
                        return MultiDict(self.form).to_dict()
                    elif self.data:
                        _, form_data, _ = parse_form_data(environ=self.environ, stream_factory=stream_factory)
                        return MultiDict(form_data).to_dict()
        return {}

    def send_response(self, status: int = 200, content: Any = None, headers: Optional[Dict[str, Any]] = None, mimetype: Optional[str] = None) -> _Response:
        from master.core.server import classes
        headers = headers or {}
        if self.endpoint and self.endpoint.parameters['content']:
            mimetype = self.endpoint.parameters['content']
        if isinstance(content, dict):
            content = json.dumps(content)
            if not mimetype and not headers.get('Content-Type') and self.accept_mimetypes.accept_json:
                mimetype = 'application/json'
        if not mimetype and not headers.get('Content-Type'):
            if self.accept_mimetypes.accept_html:
                mimetype = 'text/html'
            elif self.accept_mimetypes.accept_json:
                mimetype = 'application/json'
        return classes.Response(status=status, response=content, headers=headers, mimetype=mimetype)


class Response(BaseClass, _Response):
    def __call__(self, *args, **kwargs):
        if not self.data and self.status_code == 200:
            self.status_code = 204
        return super().__call__(*args, **kwargs)


class Endpoint:
    __slots__ = ('name', 'modules', 'parameters', 'options')

    def __init__(self, func: Callable, parameters: Dict[str, Any], options: Dict[str, Any]):
        self.options: Dict[str, Any] = options
        self.parameters: Dict[str, Any] = parameters
        self.name: str = func.__name__
        self.modules: Set[str] = set()
        module = self.module_name(func)
        if module:
            self.modules.add(module)

    @staticmethod
    def module_name(func: Callable) -> Optional[str]:
        module: str = func.__module__
        module_path = 'master.addons.'
        if module.startswith(module_path):
            return module[len(module_path):].split('.')[0]
        else:
            return None

    @staticmethod
    def clear(func: Callable):
        for url in list(methods.keys()):
            if url in methods and methods[url].name == func.__name__:
                del methods[url]

    @classmethod
    def register(cls, urls: List[str], func: Callable, *args, **kwargs):
        kwargs['func'] = func
        for url in urls:
            if not url.startswith('/'):
                url = '/' + url
            if url not in methods or methods[url].name != func.__name__:
                methods[url] = cls(*args, **kwargs)
            else:
                module = cls.module_name(func)
                if module:
                    methods[url].modules.add(module)


methods: Dict[str, Endpoint] = {}
local = Local()


# noinspection PyMethodMayBeStatic
class Controller(BaseClass):
    def _page_404(self, error: Exception) -> _Response:
        return request.send_response(status=404,
                                     content=translate(str(error)),
                                     mimetype='text/html')

    def raise_exception(self, status: int, error: Exception) -> _Response:
        method_name = f'_page_{status}'
        if request.accept_mimetypes.accept_html and hasattr(self, method_name):
            return getattr(self, method_name)(error)
        return request.send_response(status=status, content=translate(str(error)))

    def with_exception(self, error: Exception) -> _Response:
        if isinstance(error, HTTPException) and hasattr(error, 'code'):
            return self.raise_exception(error.code, error)
        raise error

    def middleware(self) -> Optional[_Response]:
        method = getattr(self, request.endpoint.name, None)
        if not method or not callable(method):
            raise AttributeError(translate('URL not associated with method within the controller, check {}').format(request.endpoint.name))
        parameters = set()
        for parameter in inspect_signature(method).parameters.values():
            request.values_dict.setdefault(parameter.name, None)
            parameters.add(parameter.name)
        for key in request.values_dict.keys():
            if key not in parameters:
                del request.values_dict[key]
        return method(**request.values_dict)

    @lazy_property
    def origins(self):
        origin_set = set()
        for element in (request.endpoint.parameters['origins'] or '').strip().split(','):
            element = element.strip()
            if element:
                origin_set.add(element)
        if not origin_set:
            for element in (arguments['origins'] or '').strip().split(','):
                element = element.strip()
                if element:
                    origin_set.add(element)
        if '*' in origin_set:
            return set()
        elif 'localhost' in origin_set:
            origin_set.remove('localhost')
            origin_set.add('127.0.0.1')
        return origin_set

    # noinspection PyUnusedLocal
    def authorize(self) -> Optional[_Response]:
        if request.endpoint.parameters['csrf']:
            if not request.csrf_token:
                raise Forbidden()
            else:
                # TODO: Validate the crsf token
                pass
        if request.endpoint.name.startswith('_') and not request.is_localhost() and (not request.authorization or request.authorization != token):
            raise Unauthorized()
        origins_set = self.origins
        if origins_set and request.get_client_ip() not in origins_set:
            raise Forbidden()
        return None

    def __call__(self) -> _Response:
        try:
            response = self.authorize() or self.middleware()
        except Exception as error:
            return self.with_exception(error)
        if not response:
            response = request.send_response()
        elif not isinstance(response, _Response):
            response = request.send_response(content=response)
        return response

    def map_rules(self, modules: List[str]) -> Generator[Rule, None, None]:
        if arguments['pipeline']:
            endpoint_type = arguments['pipeline_mode']
        else:
            endpoint_type = PipelineMode.INSTANCE.value
        modules, urls = set(modules), []
        for url, endpoint in methods.items():
            endpoint_modules: Set[str] = endpoint.modules
            endpoint_types: List[str] = endpoint.parameters['mode']
            if endpoint_modules.issubset(modules) and endpoint_type in endpoint_types:
                options: Dict[str, Any] = endpoint.options.copy()
                options['string'] = url
                options['endpoint'] = endpoint
                options['methods'] = endpoint.parameters['methods']
                options.setdefault('merge_slashes', True)
                options.setdefault('websocket', False)
                yield Rule(**options)

    def map_urls(self, converters: Optional[Dict[str, Type[BaseConverter]]] = None) -> Map:
        converters = converters or {}
        from master.core.server import classes, modules
        converters.setdefault('datetime', classes.DateTimeConverter)
        return Map(rules=self.map_rules(modules), converters=converters)
