from typing import Optional, Type
from master.orm import models, fields
from master.core.orm.fields import Field
from master.tools.misc import is_field_norm_compliant

BASE_MODEL = 'base.model'


# noinspection PyProtectedMember
class AbstractModel(models.AbstractModel):
    _name = BASE_MODEL

    id = fields.Id(label='ID')
    active = fields.Boolean(label='Active', default=True)

    @classmethod
    def _attach_klass(cls) -> Optional[Type['AbstractModel']]:
        result = super()._attach_klass()
        for element in dir(cls):
            if not isinstance(getattr(cls, element), Field):
                continue
            if not is_field_norm_compliant(element):
                raise ValueError(f'Field {cls.__module__}.{cls.__name__}.{element} is not norm compliant')
        return result


# noinspection PyProtectedMember
class Model(models.Model):
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
        if result and getattr(result, '_name', None) != BASE_MODEL and BASE_MODEL not in getattr(result, '_inherit', []):
            # Insert `BASE_MODEL` as the first inherited model
            result._inherit.insert(0, BASE_MODEL)
        return result
