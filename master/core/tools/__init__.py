import re
from typing import Type, List
from . import sql
from . import typing
from . import files
from . import config


def is_valid_name(string: str) -> bool:
    pattern = r'^[_A-Z][a-zA-Z]*$'
    return bool(re.match(pattern, string))


def simplify_class_name(string: str) -> str:
    result = ''
    for index, char in enumerate(string):
        if char.isupper() and index != 0:
            result += '_'
        result += char.lower()
    return result


def filter_class(class_list: List[Type]):
    valid_elements = []
    if len(class_list) == 1:
        valid_elements = class_list
    elif len(class_list) > 1:
        for cls in reversed(class_list):
            if not any(cls in _class.__mro__[1:] for _class in class_list if _class != cls):
                valid_elements.append(cls)
    return valid_elements
