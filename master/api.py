from functools import wraps
from typing import Callable, Any, Type, Dict, Optional, Union, List
import threading

from master.tools.collection import is_complex_iterable


class ThreadSafeVariable:
    def __init__(self, initial_value=None):
        self._value = initial_value
        self._lock = threading.RLock()

    def set_value(self, value):
        with self._lock:
            self._value = value

    def get_value(self):
        with self._lock:
            return self._value


def check_lock(func: Callable):
    @wraps(func)
    def _wrapper(self, *args, **kwargs):
        if not hasattr(self, '_lock'):
            raise AttributeError('Instance must have "_lock" attribute for thread safety.')
        with getattr(self, '_lock'):
            return func(self, *args, **kwargs)
    return _wrapper


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
    __slots__ = ('__func__', '_name')
    _register: Dict[str, Any] = {}
    _lock = threading.RLock()

    def __init__(self, func: Callable):
        super().__init__(func)
        self._name = func.__name__

    def __read_name(self, owner: Type[object]):
        return f'{owner.__module__}.{owner.__name__}.{self._name}'

    def __get__(self, instance: Optional[object], owner: Type[object]) -> Any:
        func_name = self.__read_name(owner)
        with self._lock:
            if func_name not in self._register:
                self._register[func_name] = super().__get__(instance, owner)
            return self._register[func_name]

    def __set__(self, instance: object, value: Any) -> None:
        func_name = self.__read_name(instance.__class__)
        with self._lock:
            self._register[func_name] = value


def route(urls: Union[str, List[str]], methods: Optional[Union[str, List[str]]] = None, auth: Optional[str] = None, mode: Optional[Union[str, List[str]]] = None, origins: Optional[str] = None):
    if not auth:
        auth = 'public'
    if not methods:
        methods = ['GET', 'OPTIONS', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'TRACE']
    elif not is_complex_iterable(methods):
        methods = [methods.strip().upper()]
    else:
        methods = [value.strip().upper() for value in methods]
    if not mode:
        mode = ['instance']
    elif not is_complex_iterable(mode):
        mode = [mode.strip().lower()]
    else:
        mode = [value.strip().lower() for value in mode]

    def _(func: Callable):
        from master.core.endpoints import Endpoint
        Endpoint.register(urls, func, {
            'auth': auth,
            'methods': methods,
            'mode': mode,
            'origins': origins,
        })
        return func
    return _


def clear_route(func: Callable):
    from master.core.endpoints import Endpoint
    Endpoint.clear(func)
    return func
