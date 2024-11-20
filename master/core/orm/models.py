from collections import defaultdict
from master.core.api import Class
from typing import Optional, List, Type, Union

models = defaultdict(list)


class AbstractModel(Class):
    """
    Base class for models, providing dynamic inheritance and registration in the `models` registry.
    """
    __meta_path__ = 'master.core.orm.AbstractModel'
    _inherit: Optional[Union[str, List[str]]] = None
    _name: Optional[str] = None

    @classmethod
    def _attach_klass(cls) -> Optional[Type['AbstractModel']]:
        """
        Dynamically attaches the class to the `models` registry based on its `_name`.
        Returns:
            cls: The class itself if `_name` is valid, or None otherwise.
        """
        # Handle inheritance relationships
        if 'Model' in globals():
            if not cls._inherit:
                cls._inherit = []
            elif not isinstance(cls._inherit, list):
                cls._inherit = [cls._inherit]
            # If `_name` is not set, use the last inherited model name
            if not cls._name and cls._inherit:
                cls._name = cls._inherit[-1]
        # Register the class if `_name` is valid
        if cls._name:
            models[cls._name].append(cls)
            return cls
        return None


class TransientModel(AbstractModel):
    __meta_path__ = 'master.core.orm.TransientModel'


class Model(TransientModel):
    __meta_path__ = 'master.core.orm.Model'
