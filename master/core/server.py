import logging
import time
from contextlib import contextmanager
from typing import Optional, List
from werkzeug.routing import Map
from werkzeug.serving import make_server, WSGIRequestHandler

from master.core import arguments
from master.core.db import postgres_admin_connection, mongo_admin_connection
from master.core.endpoints import Controller
from master.core.modules import default_installed_modules
from master.core.registry import ClassManager
from master.core.threads import worker, ThreadManager

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
    loading = False
    requests_count = 0

    def __init__(self):
        self._server = None

    @worker
    def run(self):
        self._server.handle_request()

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
                                   threaded=True)
        # Set a timeout (2 seconds) to check for the stop event periodically
        self._server.timeout = 2
        ThreadManager.allow.set()

    @contextmanager
    def dispatch_request(self, request):
        attempt = 60
        while self.loading and attempt >= 0:
            time.sleep(1)
            attempt -= 1
        if self.loading:
            yield controller.raise_exception(503, ConnectionAbortedError('Server is busy'))
        else:
            self.__class__.requests_count += 1
            adapter = Map(controller.map_urls(modules)).bind_to_environ(request.environ)
            try:
                endpoint, values = adapter.match()
                request.endpoint = endpoint
            except Exception as e:
                yield controller.raise_exception(404, e)
                values = {}
            try:
                if request.endpoint:
                    values.update(request.read_content())
                    yield controller.middleware(values)
            except Exception as e:
                yield controller.raise_exception(500, e)
            self.__class__.requests_count -= 1

    def __call__(self, *args, **kwargs):
        request = classes.Request(*args, **kwargs)
        with self.dispatch_request(request) as response:
            closing_iterator = response(*args, **kwargs)
        del request
        return closing_iterator
