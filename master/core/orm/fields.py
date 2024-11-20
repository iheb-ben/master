from master.core.api import Class


class Field(Class):
    __slots__ = ('label', 'groups', 'unique', 'required')

    def __init__(self, label=None, groups=None, required=False, unique=False):
        self.label = label
        self.groups = groups or []
        self.required = required
        self.unique = unique

    def type(self):
        return None

    @classmethod
    def parse(cls, value):
        return value

    @classmethod
    def bake(cls, value):
        return value


class Char(Field):
    __meta_path__ = 'master.core.orm.Char'
    __slots__ = tuple(['label'] + list(Field.__slots__))

    def __init__(self, length=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.length = length

    def type(self):
        if self.length:
            return f'VARCHAR({self.length})'
        return 'VARCHAR'

    @classmethod
    def bake(cls, value):
        return str(value)


class Integer(Field):
    __meta_path__ = 'master.core.orm.Integer'

    def type(self):
        return 'INTEGER'

    @classmethod
    def bake(cls, value):
        try:
            return int(value)
        except ValueError:
            return None
