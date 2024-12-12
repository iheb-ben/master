from functools import wraps
from typing import Callable, Any, Type, Dict, Optional, Union, List, Iterable
import threading

from master.tools.collection import is_complex_iterable, ImmutableDict


def check_lock(func: Callable):
    @wraps(func)
    def _wrapper(self, *args, **kwargs):
        if hasattr(self, '_lock'):
            with self._lock:
                return func(self, *args, **kwargs)
        return func(self, *args, **kwargs)
    return _wrapper


class ThreadSafeVariable:
    __slots__ = ('_value', '_lock')

    def __init__(self, initial_value: Any = None):
        self._value = initial_value
        self._lock = threading.RLock()

    @property
    @check_lock
    def value(self):
        return self._value

    @value.setter
    @check_lock
    def value(self, value: Any = None):
        self._value = value


# noinspection PyPep8Naming
class lazy_property:
    """A decorator for lazy, cached properties."""
    __slots__ = ('__func__', '_name')

    def __init__(self, func: Callable):
        self.__func__ = func
        self._name = func.__name__

    def __get__(self, instance: Optional[object], owner: Type[object]) -> Any:
        if instance is None:
            return self
        if self._name not in instance.__dict__:
            instance.__dict__[self._name] = self.__func__(instance)
        return instance.__dict__[self._name]

    def __set__(self, instance: object, value: Any) -> None:
        instance.__dict__[self._name] = value

    def __delete__(self, instance: object) -> None:
        if self._name in instance.__dict__:
            del instance.__dict__[self._name]


# noinspection PyPep8Naming
class classproperty:
    """
    A decorator for defining class-level properties.
    """
    __slots__ = '__func__'

    def __init__(self, func: Callable):
        self.__func__ = func

    def __get__(self, instance: Optional[object], owner: Type[object]) -> Any:
        return self.__func__(owner)


# noinspection PyPep8Naming
class lazy_classproperty(classproperty):
    """A lazy, cached class-level property."""
    _register: Dict[str, Any] = {}
    _lock = threading.RLock()

    def __read_name(self, owner: Type[object]):
        return f'{owner.__module__}.{owner.__qualname__}.{self.__func__.__name__}'

    @check_lock
    def __get__(self, instance: Optional[object], owner: Type[object]) -> Any:
        func_name = self.__read_name(owner)
        if func_name not in self._register:
            self._register[func_name] = super().__get__(instance, owner)
        return self._register[func_name]

    @check_lock
    def __set__(self, instance: object, value: Any) -> None:
        self._register[self.__read_name(instance.__class__)] = value


def route(urls: Union[str, List[str]], methods: Optional[Union[str, List[str]]] = None, auth: Optional[str] = None, mode: Optional[Union[str, List[str]]] = None, origins: Optional[str] = None, content: Optional[str] = None, csrf: bool = False):
    from master.core.parser import PipelineMode
    from master.core.endpoints import Endpoint
    if not auth:
        auth = 'public'
    assert auth in ('public', 'user')
    default_methods = ['GET', 'OPTIONS', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'TRACE']
    if not methods:
        methods = default_methods
    elif not is_complex_iterable(methods):
        methods = [methods.strip().upper()]
    else:
        methods = [value.strip().upper() for value in methods]
    assert isinstance(methods, Iterable) and all(value in default_methods for value in methods)
    if not mode:
        mode = [PipelineMode.INSTANCE.value]
    elif not is_complex_iterable(mode):
        mode = [mode.strip().lower()]
    else:
        mode = [value.strip().lower() for value in mode]
    assert isinstance(mode, Iterable) and all(PipelineMode.from_value(value) for value in mode)
    assert not origins or isinstance(origins, str)
    assert not content or isinstance(content, str)

    def _(func: Callable):
        Endpoint.register(urls, func, ImmutableDict({
            'auth': auth,
            'methods': methods,
            'mode': mode,
            'origins': origins,
            'content': content,
            'csrf': csrf,
        }))
        return func
    return _


def clear_route(func: Callable):
    from master.core.endpoints import Endpoint
    Endpoint.clear(func)
    return func
