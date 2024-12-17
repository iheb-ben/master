from datetime import datetime
from typing import AnyStr
from werkzeug.routing import BaseConverter


class DateTimeConverter(BaseConverter):
    """
    A custom URL converter for handling datetime objects in URLs.
    """

    # noinspection PyShadowingBuiltins
    def __init__(self, map, date_format='%Y-%m-%d', *args, **kwargs):
        super().__init__(map, *args, **kwargs)
        self.date_format = date_format

    def to_python(self, value: AnyStr):
        """
        Converts the URL string into a datetime object.
        """
        try:
            return datetime.strptime(value, self.date_format)
        except ValueError:
            raise ValueError(f"Invalid date format: {value}. Expected {self.date_format}.")

    def to_url(self, value: datetime):
        """
        Converts a datetime object back into a string for the URL.
        """
        return value.strftime(self.date_format)
