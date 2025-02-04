import atexit
import traceback
from threading import Event
from werkzeug import wrappers
from werkzeug.exceptions import ServiceUnavailable, NotFound
from werkzeug.serving import make_server, ThreadedWSGIServer
from .http import Request, Controller, build_controller_class, build_converters_class
from .static import StaticFilesMiddleware
from master.core.tools.config import environ
from master.core.database.connector import PoolManager
from master.core.module import modules_paths, attach_order, select_addons


class Application:
    __slots__ = ('_controller', 'paths', 'pool', 'registry', 'installed', 'to_update')
    reload_event = Event()
    stop_event = Event()

    def __init__(self, pool: PoolManager):
        self.pool = pool
        self.paths = {}
        self.registry = {}
        self.installed = []
        self.to_update = []
        self._controller = Controller()
        atexit.register(self.shutdown)

    def reload(self):
        self.paths = modules_paths()
        with self.pool.get_cursor() as cursor:
            self.installed, self.to_update = select_addons(cursor)
            attach_order(self.paths, self.installed)
        compiled = build_controller_class(self.installed)
        self._controller = compiled(
            converters=build_converters_class(self.installed),
            application=self,
        )
        self.reload_event.clear()

    def shutdown(self):
        self.stop_event.set()

    def dispatch(self, request, werkzeug_environ, start_response):
        with request.create_environment() as erp_environ:
            request.env = erp_environ
            closing_iterator = self._controller.dispatch()(werkzeug_environ, start_response)
            erp_environ.flush()
        return closing_iterator

    def __call__(self, werkzeug_environ, start_response):
        httprequest = wrappers.Request(werkzeug_environ)
        request = Request(self, httprequest)
        try:
            if request.httprequest.path.startswith(f'/{StaticFilesMiddleware.PREFIX}/'):
                return wrappers.Response(status=404)(werkzeug_environ, start_response)
            if self.reload_event.is_set():
                request.error = ServiceUnavailable()
                if httprequest.method != 'GET' or not httprequest.accept_mimetypes.accept_html:
                    return wrappers.Response(status=request.error.code)(werkzeug_environ, start_response)
                request.error.traceback = traceback.format_stack()
            return self.dispatch(request, werkzeug_environ, start_response)
        finally:
            del request
            del httprequest


def start_server(pool: PoolManager):
    server: ThreadedWSGIServer = make_server(
        host='localhost',
        port=environ['PORT'],
        app=StaticFilesMiddleware(app=Application(pool)),
        threaded=True,
    )
    server.timeout = 1
    server.app.reload()
    while not server.app.stop_event.is_set():
        server.handle_request()
        if server.app.reload_event.is_set():
            server.app.reload()
    server.server_close()
