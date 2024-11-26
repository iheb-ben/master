from collections import defaultdict
from typing import Optional, List, Union

from master.api import lazy_classproperty
from master.core.registry import BaseClass
from master.tools.collection import is_complex_iterable

structure = defaultdict(list)


class AbstractModel(BaseClass):
    _inherit: Optional[Union[List[str], str]] = None
    _name: Optional[str] = None

    @classmethod
    def _before_register(cls):
        if not cls._inherit:
            cls._inherit = []
        if not is_complex_iterable(cls._inherit):
            cls._inherit = [cls._inherit]
        if not cls._name and cls._inherit:
            cls._name = cls._inherit[-1]

    @classmethod
    def _ignore_register(cls):
        if cls._name:
            structure[cls._name].insert(0, cls)

    # noinspection PyMethodParameters
    @lazy_classproperty
    def __meta__(cls) -> Optional[str]:
        if cls._name:
            return None
        return super().__meta__


class TransientModel(AbstractModel):
    # noinspection PyMethodParameters
    @lazy_classproperty
    def __meta__(cls) -> Optional[str]:
        if cls._name:
            return None
        return f'{__name__}.TransientModel'


class Model(TransientModel):
    # noinspection PyMethodParameters
    @lazy_classproperty
    def __meta__(cls) -> Optional[str]:
        if cls._name:
            return None
        return f'{__name__}.Model'
