from master.api import lazy_classproperty
from master.core.registry import BaseClass


class AbstractModel(BaseClass):
    pass


class TransientModel(AbstractModel):
    # noinspection PyMethodParameters
    @lazy_classproperty
    def __meta__(cls) -> str:
        return f'{__name__}.TransientModel'


class Model(TransientModel):
    # noinspection PyMethodParameters
    @lazy_classproperty
    def __meta__(cls) -> str:
        return f'{__name__}.Model'
