from typing import Union, List, Dict, Any, Callable, Optional
from werkzeug.local import Local
from werkzeug.routing import Rule
from werkzeug.wrappers import Request as _Request, Response

from master import request
from master.core import arguments
from master.core.registry import BaseClass
from master.tools.collection import is_complex_iterable

# Store methods names with annotation api.route
methods = {}
local = Local()


# noinspection PyMethodMayBeStatic
class Request(BaseClass, _Request):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint: Optional[Endpoint] = None
        setattr(local, 'request', self)

    def raise_exception(self, status, error):
        return Response(status=status, response=str(error))

    def __del__(self):
        setattr(local, 'request', None)
        super().__del__()


class Endpoint:
    __slots__ = ('name', 'module', 'parameters')

    def __init__(self, func: Callable, parameters: Dict[str, Any]):
        self.parameters = parameters
        self.name = func.__name__
        self.module = func.__module__
        if self.module.startswith('master.addons.'):
            self.module = self.module.split('.')[2]
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
    def raise_exception(self, status, error):
        return request.raise_exception(status, error)

    # noinspection PyUnusedLocal
    def middleware(self, values: Dict[str, Any]):
        controller_function: Callable = getattr(self, request.endpoint.name)
        return controller_function(**values)

    def map_urls(self, modules):
        if arguments['pipeline']:
            endpoint_type = arguments['pipeline_mode']
        else:
            endpoint_type = 'instance'
        urls = []
        for url, endpoint in methods.items():
            endpoint_types = endpoint.parameters['mode']
            if endpoint.module in modules and endpoint_type in endpoint_types:
                urls.append(Rule(url, endpoint=endpoint, methods=endpoint.parameters['methods']))
        return urls
