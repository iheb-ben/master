from os import PathLike
from pathlib import Path
from typing import Type, Any, Union

SystemPath = Union[Path, PathLike, str]


def cast_string(o: str, value_type: Type) -> Any:
    assert value_type is not None
    if o is None:
        return None
    elif value_type == bool:
        return o.lower() in ('true', '1', 'yes')
    elif type(o) is value_type:
        return o
    return value_type(o)
