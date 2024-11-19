from abc import ABCMeta, ABC, abstractmethod
from collections import defaultdict
from typing import Dict, Any, List, Callable
from master.core.api import Meta


class ABCMetaModel(ABCMeta, Meta):
    pass


class Interface(ABC):
    @abstractmethod
    def create(self, values: Dict[str, Any]) -> 'Any':
        """Create a new record."""
        pass

    @abstractmethod
    def read(self, domain: List[Any], fields: List[str]) -> 'List[Dict]':
        """Read records fields."""
        pass

    @abstractmethod
    def write(self, values: Dict[str, Any]) -> bool:
        """Update current records."""
        pass

    @abstractmethod
    def unlink(self) -> None:
        """Remove current records."""
        pass


models = defaultdict(list)
_base_models_defined: Callable[[], bool] = lambda: 'Model' in globals()


class AbstractModel(metaclass=ABCMetaModel):
    @classmethod
    def _attach_klass(cls):
        if _base_models_defined():
            if not hasattr(cls, '_inherit'):
                cls._inherit = []
            if not isinstance(cls._inherit, list):
                cls._inherit = [cls._inherit]
            if not hasattr(cls, '_name') and cls._inherit:
                cls._name = cls._inherit[-1]
        if hasattr(cls, '_name'):
            models[cls._name].append(cls)


class TransientModel(AbstractModel, Interface, ABC, metaclass=ABCMetaModel):
    pass


class Model(TransientModel, ABC, metaclass=ABCMetaModel):
    @classmethod
    def _attach_klass(cls):
        super()._attach_klass()
        basic_model = 'base.model'
        if _base_models_defined() and getattr(cls, '_name', None) != basic_model and basic_model not in getattr(cls, '_inherit', []):
            cls._inherit.insert(0, basic_model)
