from typing import Optional, Type
from master.core import orm

BASE_MODEL = 'base.model'


class AbstractModel(orm.AbstractModel):
    _name = BASE_MODEL


class Model(orm.Model):
    """
    A concrete model class with additional logic to enforce inheritance from `BASE_MODEL`.
    """

    @classmethod
    def _attach_klass(cls) -> Optional[Type['Model']]:
        """
        Attaches the class to the `models` registry and ensures inheritance from `BASE_MODEL`.
        Returns:
            cls: The class itself if `_name` is valid, or None otherwise.
        """
        result = super()._attach_klass()
        if result:
            if (
                getattr(result, '_name', None) != BASE_MODEL and
                BASE_MODEL not in getattr(result, '_inherit', [])
            ):
                # Insert `BASE_MODEL` as the first inherited model
                if not isinstance(result._inherit, list):
                    result._inherit = []
                result._inherit.insert(0, BASE_MODEL)
        return result
