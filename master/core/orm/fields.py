from typing import Any, Optional
from master.core.api import Class


class Field(Class):
    __slots__ = ('label', 'groups', 'unique', 'required', 'default')

    def __init__(self, label=None, groups=None, required=False, unique=False, default=None):
        self.label = label
        self.groups = groups or []
        self.required = required
        self.unique = unique
        self.default = default

    def type(self) -> None:
        return None

    @classmethod
    def parse(cls, value: Any) -> Any:
        return value

    @classmethod
    def bake(cls, value: Any) -> Any:
        return value


class Id(Field):
    __meta_path__ = 'master.orm.fields.Id'

    def __init__(self, label=None):
        super().__init__(label=label)


class Boolean(Field):
    __meta_path__ = 'master.orm.fields.Boolean'

    def type(self) -> str:
        return 'BOOLEAN'

    @classmethod
    def bake(cls, value) -> Optional[bool]:
        if value is not None:
            return True if value else False
        return value


class Char(Field):
    __meta_path__ = 'master.orm.fields.Char'
    __slots__ = tuple(['length'] + list(Field.__slots__))

    def __init__(self, length=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.length = length

    def type(self) -> str:
        if self.length:
            return f'VARCHAR({self.length})'
        return 'VARCHAR'

    @classmethod
    def bake(cls, value: Any) -> Optional[str]:
        result = super().bake(value)
        if result is not None:
            return str(value)
        return result


class Integer(Field):
    __meta_path__ = 'master.orm.fields.Integer'

    def type(self) -> str:
        return 'INTEGER'

    @classmethod
    def bake(cls, value: Any) -> Optional[int]:
        try:
            return int(super().bake(value))
        except ValueError:
            return None
