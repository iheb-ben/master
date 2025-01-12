from datetime import datetime
from werkzeug.routing import BaseConverter


class ListConverter(BaseConverter):
    def to_python(self, value):
        return value.split(',')

    def to_url(self, values):
        return ','.join(super(ListConverter, self).to_url(value) for value in values)


# noinspection PyArgumentList,PyShadowingBuiltins
class DateTimeConverter(BaseConverter):
    def __init__(self, map, date_format='%Y-%m-%dT%H:%M:%S', *args, **kwargs):
        super().__init__(map, *args, **kwargs)
        self.date_format = date_format

    def to_python(self, value: str):
        try:
            return datetime.strptime(value, self.date_format)
        except ValueError:
            raise ValueError(f"Invalid date format: {value}. Expected {self.date_format}.")

    def to_url(self, value: datetime):
        return value.strftime(self.date_format)
