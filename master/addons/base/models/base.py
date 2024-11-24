from typing import Optional, Type
from master.core.orm import models, fields
from master.tools.misc import is_field_norm_compliant


# noinspection PyProtectedMember
class AbstractModel(models.AbstractModel):
    _name = 'base.model'

    id = fields.Id(label='ID')
    active = fields.Boolean(label='Active', default=True)

    @classmethod
    def _attach_klass(cls):
        super()._attach_klass()
        for element in dir(cls):
            if not isinstance(getattr(cls, element), fields.Field):
                continue
            if not is_field_norm_compliant(element):
                raise ValueError(f'Field {cls.__module__}.{cls.__name__}.{element} is not norm compliant')


# noinspection PyProtectedMember
class Model(models.Model):
    """
    A concrete model class with additional logic to enforce inheritance from `BASE_MODEL`.
    """

    @classmethod
    def _attach_klass(cls):
        """
        Attaches the class to the `models` registry and ensures inheritance from `BASE_MODEL`.
        """
        super()._attach_klass()
        if cls._name and cls._name != AbstractModel._name and AbstractModel._name not in cls._inherit:
            # Insert `BASE_MODEL` as the first inherited model
            cls._inherit.insert(0, AbstractModel._name)
