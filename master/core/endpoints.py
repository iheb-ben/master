import json
import logging
from pathlib import Path
from typing import Union, List, Dict, Any, Callable, Optional, Generator, Set
from werkzeug.exceptions import UnsupportedMediaType, HTTPException, Unauthorized, InternalServerError
from werkzeug.local import Local
from werkzeug.routing import Rule
from werkzeug.wrappers import Request as _Request, Response as _Response

from master import request
from master.core import arguments, signature
from master.core.db import translate
from master.core.parser import PipelineMode
from master.core.registry import BaseClass
from master.tools.collection import is_complex_iterable

_logger = logging.getLogger(__name__)
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

    def get_client_ip(self) -> str:
        """
        Extract the client's IP address, considering proxies.
        """
        # Check for the X-Forwarded-For header (proxies)
        if 'X-Forwarded-For' in self.headers:
            # Split the header to get the first IP (original client)
            forwarded_ips = self.headers['X-Forwarded-For'].split(',')
            original_ip = forwarded_ips[0].strip()
            return original_ip
        # Fallback to remote address if no proxy header exists
        return self.remote_addr

    def is_localhost(self) -> bool:
        """
        Check if the IP address is localhost.
        """
        localhost_ips = {'127.0.0.1', '::1'}
        if signature['public_ip']:
            localhost_ips.add(signature['public_ip'])
        return self.get_client_ip() in localhost_ips

    def read_parameters(self) -> Dict[str, Any]:
        try:
            return self.json
        except UnsupportedMediaType:
            return {}

    def send_response(self, status: int = 200, content: Any = None, headers: Optional[Dict[str, Any]] = None, mimetype: Optional[str] = None):
        from master.core.server import classes
        headers = headers or {}
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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.render_template: Optional[str] = None
        self.template_context: Optional[Dict[str, Any]] = None

    def __call__(self, *args, **kwargs):
        # TODO: build the template
        return super().__call__(*args, **kwargs)


class Endpoint:
    __slots__ = ('name', 'modules', 'parameters')

    def __init__(self, func: Callable, parameters: Dict[str, Any]):
        self.parameters = parameters
        self.name: str = func.__name__
        self.modules = set()
        module = self.module_name(func)
        if module:
            self.modules.add(module)

    @staticmethod
    def module_name(func: Callable) -> Optional[str]:
        module: str = func.__module__
        if module.startswith('master.addons.'):
            return module.split('.')[2]
        else:
            return None

    @classmethod
    def register(cls, urls: Union[str, List[str]], func: Callable, parameters: Dict[str, Any]):
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

    def middleware(self, values: Dict[str, Any]):
        return getattr(self, request.endpoint.name)(**values)

    def __call__(self, values: Dict[str, Any]):
        try:
            if request.endpoint.name.startswith('_') and not request.is_localhost():
                raise Unauthorized()
            response = self.middleware(values)
        except Exception as error:
            return self.with_exception(error)
        if not response:
            response = request.send_response()
        elif not isinstance(response, _Response):
            response = request.send_response(content=response)
        return response

    def map_urls(self, modules):
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
