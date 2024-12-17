from werkzeug.routing import BaseConverter, Map


class DateTimeConverter(BaseConverter):
    """
    A custom URL converter for handling datetime objects in URLs.
    """
    def __init__(self, date_format='%Y-%m-%d', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.date_format = date_format

    def to_python(self, value):
        """
        Converts the URL string into a datetime object.
        """
        try:
            return datetime.strptime(value, self.date_format)
        except ValueError:
            raise ValueError(f"Invalid date format: {value}. Expected {self.date_format}.")

    def to_url(self, value):
        """
        Converts a datetime object back into a string for the URL.
        """
        return value.strftime(self.date_format)
