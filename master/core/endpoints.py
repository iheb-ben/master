from pathlib import Path
from typing import Union, List, Dict, Any, Callable, Optional, Generator
from werkzeug.local import Local
from werkzeug.routing import Rule
from werkzeug.wrappers import Request as _Request, Response as _Response

from master import request
from master.core import arguments
from master.core.db import translate
from master.core.registry import BaseClass
from master.exceptions import AccessDeniedError
from master.tools.collection import is_complex_iterable

# Store methods names with annotation api.route
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
        return self.get_client_ip() in localhost_ips

    def send_response(self, status: int = 200, content: Any = None, headers: Optional[Dict[str, Any]] = None, mimetype: Optional[str] = None):
        from master.core.server import classes
        return classes.Response(status=status, response=content, headers=headers, mimetype=mimetype)

    def render(self, template_xml_id: str, context: Optional[Dict[str, Any]] = None):
        response = self.send_response(status=200, mimetype='text/html')
        response.render_template = template_xml_id
        response.template_context = context or {}
        return response


class Response(BaseClass, _Response):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.render_template: Optional[str] = None
        self.template_context: Optional[Dict[str, Any]] = None

    def __call__(self, *args, **kwargs):
        # TODO: build the template
        return super().__call__(*args, **kwargs)


class Endpoint:
    __slots__ = ('name', 'module', 'parameters')

    def __init__(self, func: Callable, parameters: Dict[str, Any]):
        self.parameters = parameters
        self.name: str = func.__name__
        module: str = func.__module__
        if module.startswith('master.addons.'):
            self.module = module.split('.')[2]
        else:
            self.module = None

    @classmethod
    def register(cls, urls: Union[str, List[str]], func: Callable, parameters: Dict[str, Any]):
        if not is_complex_iterable(urls):
            urls = [urls]
        for url in urls:
            if not url.startswith('/'):
                url = '/' + url
            if url.endswith('/'):
                url = url[:-1]
            methods[url] = cls(func, parameters)


# noinspection PyMethodMayBeStatic
class Controller(BaseClass):
    def raise_exception(self, status: int, error: Exception):
        return request.send_response(status, translate(str(error)))

    def middleware(self, values: Dict[str, Any]):
        if request.endpoint.name.startswith('_') and not request.is_localhost():
            return self.raise_exception(403, AccessDeniedError('Only requests from localhost are allowed to read call this endpoint'))
        response = getattr(self, request.endpoint.name)(**values)
        if response is None:
            response = request.send_response()
        elif not isinstance(response, _Response):
            response = request.send_response(content=response)
        return response

    def map_urls(self, modules):
        if arguments['pipeline']:
            endpoint_type = arguments['pipeline_mode']
        else:
            endpoint_type = 'instance'
        urls = []
        for url, endpoint in methods.items():
            endpoint_types: List[str] = endpoint.parameters['mode']
            if endpoint.module in modules and endpoint_type in endpoint_types:
                urls.append(Rule(url, endpoint=endpoint, methods=endpoint.parameters['methods']))
        return urls
