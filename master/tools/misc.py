from pathlib import Path
from tempfile import gettempdir
from typing import Any
import inspect
import random
import string
import socket
import re


def is_field_norm_compliant(field_name: str) -> bool:
    """
    Checks if the class attribute complies with naming conventions:
    - Must be entirely lowercase.
    - Can contain underscores `_` within the name.
    - Must not start or end with an underscore, nor have consecutive underscores.
    - Must not contain uppercase letters.

    Args:
        field_name (str): The class attribute name to check.

    Returns:
        bool: True if the attribute name complies, False otherwise.
    """
    pattern = r"^(?!_)(?!.*__)[a-z_]+(?<!_)$"
    return bool(re.match(pattern, field_name))


def is_class_norm_compliant(class_name: str) -> bool:
    """
    Checks if the class name complies with naming conventions:
    - Can optionally start with a single underscore `_`.
    - Must contain only uppercase and lowercase letters (A-Z, a-z).
    Args:
        class_name (str): The class name to check.
    Returns:
        bool: True if the class name complies, False otherwise.
    """
    pattern = r"^_?[A-Za-z]+$"
    return bool(re.match(pattern, class_name))


def _get_mangled_method_name(klass: Any, method_name: str) -> str:
    """
    Returns the mangled method name if the method name starts with double underscores.
    Otherwise, returns the original method name.
    :param klass: The class or instance for which to mangle the method name.
    :param method_name: The original method name.
    :return: The mangled method name if applicable, otherwise the original method name.
    """
    if method_name.startswith('__') and not method_name.endswith('__'):
        # Adjust for name-mangling (prepend _ClassName to method name)
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
    # Use the mangled method name if applicable
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
    # Get the potentially mangled method name
    method_name = _get_mangled_method_name(klass, method_name)
    # Check and call the method if it exists
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
    # Use inspect.getattr_static to get the raw method without triggering descriptors
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
    # Get the potentially mangled method name
    method_name = _get_mangled_method_name(klass, method_name)
    # Check and call the method if it exists
    if is_classmethod(klass, method_name):
        return getattr(klass, method_name)(*args, **kwargs)
    return None


def temporairy_directory():
    directory_path = Path(gettempdir()).joinpath('.master')
    if not directory_path.exists():
        directory_path.mkdir()
    return directory_path


def generate_unique_string(length=20, ignore_letters=None):
    ignore_letters = ignore_letters or ''
    characters = string.punctuation + string.ascii_letters + string.digits
    if ignore_letters:
        characters = ''.join(char for char in characters if char not in ignore_letters)
    return ''.join(random.choices(characters, k=length))


already_checked = set()


def find_available_port(port: int) -> int:
    """
    Checks if a port is available. If the provided port is in use,
    increments the port number by 1 and checks again until an available port is found.
    Args:
        port (int): The starting port number to check for availability.
    Returns:
        int: An available port number.
    Example:
        >>> find_available_port(9000)
        9000  # or the next available port if 9000 is in use
    """
    while True:
        if port in already_checked:
            port += 1
            continue
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("localhost", port))
            break
        except OSError:
            already_checked.add(port)
            port += 1
    return port


def clean_end_of_line(s: str) -> str:
    """
    Removes trailing end-of-line characters (e.g., \n, \r) and whitespace from a string.
    Args:
        s (str): The string to clean.
    Returns:
        str: The cleaned string.
    """
    return s.rstrip("\r\n")
