from collections import defaultdict, OrderedDict
from typing import Optional, List, Type, Union, Dict
from master.core.api import BaseClass


class RegisterModelManager:
    # Global register to store all models
    _register = defaultdict(list)

    def __init__(self):
        # Used to store the new built models
        self.register = {}

    def build_models(self, modules: List[str]):
        from master.core.module.loader import reorder_module_names
        for module in reversed(reorder_module_names(modules)):



class AbstractModel(BaseClass):
    """
    Base class for models, providing dynamic inheritance and registration in the `models` registry.
    """
    __meta_path__ = 'master.core.orm.AbstractModel'
    _inherit: Optional[Union[str, List[str]]] = None
    _name: Optional[str] = None

    # noinspection PyProtectedMember
    @classmethod
    def _attach_klass(cls):
        """
        Dynamically attaches the class to the `models` registry based on its `_name`.
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
        else:
            cls._name = None
        # Register the class if `_name` is valid
        if cls._name:
            RegisterModelManager._register[cls._name].append(cls)


class TransientModel(AbstractModel):
    __meta_path__ = 'master.core.orm.TransientModel'


class Model(TransientModel):
    __meta_path__ = 'master.core.orm.Model'
