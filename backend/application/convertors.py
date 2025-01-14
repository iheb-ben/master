from datetime import datetime
from werkzeug.routing import BaseConverter


class ListConverter(BaseConverter):
    def to_python(self, value):
        return value.split(',')

    def to_url(self, values):
        return ','.join(map(lambda value: super().to_url(value), values))


# noinspection PyShadowingBuiltins
class DateTimeConverter(BaseConverter):
    __slots__ = 'date_format'

    def __init__(self, map, format):
        super().__init__(map)
        self.format = format

    def to_python(self, value: str):
        try:
            return datetime.strptime(value, self.format)
        except ValueError:
            raise ValueError(f"Invalid date format: {value}. Expected {self.format}.")

    def to_url(self, value: datetime):
        return value.strftime(self.format)
