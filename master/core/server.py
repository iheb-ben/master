import logging
import time
from contextlib import contextmanager
from typing import Optional, List
from werkzeug.exceptions import NotFound, TooManyRequests, ServiceUnavailable
from werkzeug.routing import Map
from werkzeug.serving import make_server, WSGIRequestHandler

from master.api import ThreadSafeVariable, lazy_classproperty
from master.core import arguments
from master.core.db import postgres_admin_connection, mongo_admin_connection
from master.core.endpoints import Controller
from master.core.modules import default_installed_modules
from master.core.parser import PipelineMode
from master.core.registry import ClassManager
from master.core.threads import worker, run_event
from master.tools.system import get_max_threads

_logger = logging.getLogger(__name__)
modules: List[str] = []
classes: Optional[ClassManager] = None
controller: Optional[Controller] = None


class RequestHandler(WSGIRequestHandler):
    def log_request(self, code='*', size='*'):
        remote_addr = self.client_address[0]  # Client's IP address
        method = self.command  # HTTP method (e.g., GET, POST)
        path = self.path  # Requested URL path
        http_version = self.request_version  # HTTP version
        _logger.info(f'{remote_addr} - "{method} {path} {http_version}" {code} - {size}')


class Server:
    __slots__ = '_server'
    loading = ThreadSafeVariable(False)
    requests_count = ThreadSafeVariable(0)

    def __init__(self):
        self._server = None

    @worker
    def run(self):
        self._server.handle_request()

    # noinspection PyMethodParameters
    @lazy_classproperty
    def max_threads_number(cls):
        if arguments['pipeline'] and arguments['pipeline_mode'] == PipelineMode.NODE.value:
            return 1
        else:
            return max(round(abs(get_max_threads() / 2)), 1)

    def _start(self):
        global modules, classes, controller
        modules = default_installed_modules()
        classes = ClassManager(modules)
        controller = classes.Controller()
        import master
        master.postgres_manager = classes.PostgresManager(arguments['db_name'])
        if arguments['db_mongo']:
            master.mongo_db_manager = classes.MongoDBManager(arguments['db_name'])
        self._server = make_server(host='localhost',
                                   port=arguments['port'],
                                   app=lambda *args, **kwargs: self(*args, **kwargs),
                                   request_handler=RequestHandler,
                                   threaded=self.max_threads_number > 1)
        # Set a timeout (2 seconds) to check for the stop event periodically
        self._server.timeout = 2
        run_event.set()

    @contextmanager
    def dispatch_request(self, request):
        attempt = 60
        while self.loading.get_value() and attempt >= 0:
            time.sleep(1)
            attempt -= 1
        if self.loading.get_value():
            yield controller.with_exception(ServiceUnavailable())
        elif self.requests_count.get_value() >= self.max_threads_number:
            yield controller.with_exception(TooManyRequests())
        else:
            self.requests_count.set_value(self.requests_count.get_value() + 1)
            adapter = Map(controller.map_urls(modules)).bind_to_environ(request.environ)
            try:
                request.endpoint, values = adapter.match()
            except NotFound:
                values = {}
            try:
                if request.endpoint:
                    values.update(request.read_parameters())
                    yield controller(values)
                else:
                    yield controller.with_exception(NotFound())
            except Exception:
                raise
            finally:
                self.requests_count.set_value(self.requests_count.get_value() - 1)

    def __call__(self, *args, **kwargs):
        request = classes.Request(*args, **kwargs)
        try:
            with self.dispatch_request(request) as response:
                return response(*args, **kwargs)
        except Exception:
            raise
        finally:
            del request
