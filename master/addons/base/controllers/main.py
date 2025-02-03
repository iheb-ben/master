from master.core.service.http import html_route, Controller


# noinspection PyMethodMayBeStatic
class Main(Controller):
    @html_route('/')
    def homepage(self):
        return 'Home Page'
