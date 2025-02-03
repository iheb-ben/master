from master.core.service.http import html_route
from .base import Base


# noinspection PyMethodMayBeStatic
class Main(Base):
    @html_route('/')
    def homepage(self):
        return 'Home Page'
