from typing import Union, List, Dict, Any, Callable

from master.core.registry import BaseClass
from master.tools.collection import is_complex_iterable

# Store methods names with annotation api.route
methods = {}


class Endpoint:
    __slots__ = ('url', 'name', 'parameters')

    def __init__(self, name: str, parameters: Dict[str, Any]):
        self.parameters = parameters
        self.name = name

    @classmethod
    def register(cls, urls: Union[str, List[str]], func: Callable, parameters: Dict[str, Any]):
        if not is_complex_iterable(urls):
            urls = [urls]
        for url in urls:
            if not url.startswith('/'):
                url = '/' + url
            if url.endswith('/'):
                url = url[:-1]
            methods[url] = cls(func.__name__, parameters)


class Controller(BaseClass):
    pass
