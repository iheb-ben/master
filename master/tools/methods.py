from typing import Any
import inspect


def _get_mangled_method_name(klass: Any, method_name: str) -> str:
    """
    Returns the mangled method name if the method name starts with double underscores.
    Otherwise, returns the original method name.
    :param klass: The class or instance for which to mangle the method name.
    :param method_name: The original method name.
    :return: The mangled method name if applicable, otherwise the original method name.
    """
    if method_name.startswith('__') and not method_name.endswith('__'):
        class_name = klass.__class__.__name__ if isinstance(klass, object) else klass.__name__
        return f"_{class_name}{method_name}"
    return method_name


def has_method(klass: Any, method_name: str) -> bool:
    """
    Checks if a class or instance has a method with the given name.
    :param klass: The class or instance to check.
    :param method_name: The name of the method to look for.
    :return: True if the method exists and is callable, False otherwise.
    """
    method_name = _get_mangled_method_name(klass, method_name)
    return hasattr(klass, method_name) and callable(getattr(klass, method_name))


def call_method(klass: Any, method_name: str, *args: object, **kwargs: object) -> Any:
    """
    Calls a method on a class or instance if it exists, handling name-mangled methods.
    :param klass: The class or instance to call the method on.
    :param method_name: The name of the method to call.
    :param args: Positional arguments for the method.
    :param kwargs: Keyword arguments for the method.
    :return: The result of the method call if it exists, otherwise None.
    """
    method_name = _get_mangled_method_name(klass, method_name)
    if has_method(klass, method_name):
        return getattr(klass, method_name)(*args, **kwargs)
    return None


def is_classmethod(klass: Any, method_name: str) -> bool:
    """
    Checks if a method is a class method.
    :param klass: The class or instance containing the method.
    :param method_name: The name of the method to check.
    :return: True if the method is a class method, False otherwise.
    """
    method = inspect.getattr_static(klass, _get_mangled_method_name(klass, method_name), None)
    return isinstance(method, classmethod)


def call_classmethod(klass: Any, method_name: str, *args, **kwargs) -> Any:
    """
    Calls a classmethod of a class if it exists, handling name-mangled methods.
    :param klass: The class to call the method on.
    :param method_name: The name of the method to call.
    :param args: Positional arguments for the method.
    :param kwargs: Keyword arguments for the method.
    :return: The result of the method call if it exists, otherwise None.
    """
    method_name = _get_mangled_method_name(klass, method_name)
    if is_classmethod(klass, method_name):
        return getattr(klass, method_name)(*args, **kwargs)
    return None
