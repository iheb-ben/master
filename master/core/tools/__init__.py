import re
from typing import Type, List
from . import sql
from . import typing
from . import files
from . import config


def is_valid_name(string: str) -> bool:
    pattern = r'^[_A-Z][a-zA-Z]*$'
    return bool(re.match(pattern, string))


def filter_class(class_list: List[Type]):
    valid_elements = []
    for cls in reversed(class_list):
        if not any(cls in _class.__mro__[1:] for _class in class_list if _class != cls):
            valid_elements.append(cls)
    return valid_elements
