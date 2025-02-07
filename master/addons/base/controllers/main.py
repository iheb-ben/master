from master.core.exceptions import SimulateHTTPException
from master.core.service.http import route, Response
from .base import Base


# noinspection PyMethodMayBeStatic
class Main(Base):
    @route('/_/simulate/<int:code>', rollback=False, sitemap=False)
    def route_simulate_http_error(self, code):
        raise SimulateHTTPException(code)

    @route('/')
    def route_homepage(self):
        return 'Home Page'

    @route('/hello')
    def route_hello_world(self):
        return Response(template='base.hello_world')
