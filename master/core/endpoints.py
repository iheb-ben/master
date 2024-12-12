import json
from inspect import Parameter, signature as inspect_signature
from io import BytesIO
from pathlib import Path
from typing import Union, List, Dict, Any, Callable, Optional, Generator, Set, Mapping
from werkzeug.datastructures import MultiDict
from werkzeug.exceptions import UnsupportedMediaType, HTTPException, Unauthorized, InternalServerError
from werkzeug.formparser import parse_form_data
from werkzeug.local import Local
from werkzeug.routing import Rule
from werkzeug.wrappers import Request as _Request, Response as _Response

from master import request
from master.core import arguments, signature
from master.core.db import translate
from master.core.git import token
from master.core.parser import PipelineMode
from master.core.registry import BaseClass
from master.tools.collection import is_complex_iterable

methods = {}
local = Local()


def generate_file_stream(file_path: str, chunk_size: int = 1024) -> Generator[bytes, None, None]:
    """
    Generate file content in chunks to stream it efficiently.
    :param file_path: Path to the file to be streamed.
    :param chunk_size: Size of each chunk in bytes.
    :yield: Chunk of file content.
    """
    with open(file_path, 'rb') as file:
        while chunk := file.read(chunk_size):
            yield chunk


# noinspection PyMethodMayBeStatic
class Request(BaseClass, _Request):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint: Optional[Endpoint] = None
        setattr(local, 'request', self)

    def get_client_ip(self) -> Optional[str]:
        """
        Extract the client's IP address, considering proxies.
        """
        # Check for the X-Forwarded-For header (proxies)
        proxy_header = 'X-Forwarded-For'
        if self.headers.get(proxy_header):
            # Split the header to get the first IP (original client)
            for ip in self.headers[proxy_header].split(','):
                client_ip = ip and ip.strip() or ''
                if not client_ip:
                    continue
                return client_ip
        # Fallback to remote address if no proxy header exists
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

    def send_response(self, status: int = 200, content: Any = None, headers: Optional[Dict[str, Any]] = None, mimetype: Optional[str] = None):
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
    __slots__ = ('name', 'modules', 'parameters')

    def __init__(self, func: Callable, parameters: Mapping[str, Any]):
        self.parameters: Mapping[str, Any] = parameters
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
    def register(cls, urls: Union[str, List[str]], func: Callable, parameters: Mapping[str, Any]):
        if not is_complex_iterable(urls):
            urls = [urls]
        for url in urls:
            if not url.startswith('/'):
                url = '/' + url
            if url.endswith('/'):
                url = url[:-1]
            if url not in methods or methods[url].name != func.__name__:
                methods[url] = cls(func, parameters)
            else:
                module = cls.module_name(func)
                if module:
                    methods[url].modules.add(module)


# noinspection PyMethodMayBeStatic
class Controller(BaseClass):
    def _page_404(self, error: Exception):
        return request.send_response(status=404,
                                     content=translate(str(error)),
                                     mimetype='text/html')

    def raise_exception(self, status: int, error: Exception):
        method_name = f'_page_{status}'
        if request.accept_mimetypes.accept_html and hasattr(self, method_name):
            return getattr(self, method_name)(error)
        return request.send_response(status, translate(str(error)))

    def with_exception(self, error: Exception):
        if isinstance(error, HTTPException) and hasattr(error, 'code'):
            return self.raise_exception(error.code, error)
        raise error

    def middleware(self, *args, **kwargs):
        method = getattr(self, request.endpoint.name, None)
        if not method:
            raise AttributeError(translate('URL not associated with method in the controller, check {}').format(request.endpoint.name))
        parameters = set()
        for parameter in inspect_signature(method).parameters.values():
            kwargs.setdefault(parameter.name, None)
            parameters.add(parameter.name)
        for key in kwargs.keys():
            if key not in parameters:
                del kwargs[key]
        return method(*args, **kwargs)

    @property
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
    def authorize(self, *args, **kwargs):
        if request.endpoint.name.startswith('_') and not request.is_localhost() and (not request.authorization or request.authorization != token):
            raise Unauthorized()
        origins = self.origins
        if origins and request.get_client_ip() not in origins:
            raise Unauthorized()

    def __call__(self, values: Dict[str, Any]):
        try:
            response = self.authorize(**values)
            if not response:
                response = self.middleware(**values)
        except Exception as error:
            return self.with_exception(error)
        if not response:
            response = request.send_response()
        elif not isinstance(response, _Response):
            response = request.send_response(content=response)
        return response

    def map_urls(self, modules) -> List[Rule]:
        if arguments['pipeline']:
            endpoint_type = arguments['pipeline_mode']
        else:
            endpoint_type = PipelineMode.INSTANCE.value
        modules, urls = set(modules), []
        for url, endpoint in methods.items():
            endpoint_modules: Set[str] = endpoint.modules
            endpoint_types: List[str] = endpoint.parameters['mode']
            if endpoint_modules.issubset(modules) and endpoint_type in endpoint_types:
                urls.append(Rule(url, endpoint=endpoint, methods=endpoint.parameters['methods']))
        return urls
