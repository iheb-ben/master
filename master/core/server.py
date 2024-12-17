import logging
import time
from typing import Optional, List, Any, Union
from werkzeug.exceptions import NotFound, TooManyRequests, ServiceUnavailable
from werkzeug.serving import make_server, WSGIRequestHandler

from master import request
from master.api import ThreadSafeVariable, lazy_classproperty, check_lock
from master.core import arguments
from master.core.db import postgres_admin_connection, mongo_admin_connection
from master.core.endpoints import Controller, local
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
    def log_request(self, code: Union[int, str] = '*', size: Union[int, str] = '*'):
        remote_addr = self.client_address[0]  # Client's IP address
        method = self.command  # HTTP method (e.g., GET, POST)
        path = self.path  # Requested URL path
        http_version = self.request_version  # HTTP version
        _logger.info(f'{remote_addr} - "{method} {path} {http_version}" {code}')


class Counter(ThreadSafeVariable):
    __slots__ = tuple(['_ips'] + list(ThreadSafeVariable.__slots__))

    def __init__(self):
        super().__init__(0)
        self._ips: Dict[str, int] = {}

    @check_lock
    def increase(self) -> None:
        self._value += 1
        ip = request.get_client_ip()
        if ip and not request.is_localhost():
            self._ips.setdefault(ip, 0)
            self._ips[ip] += 1

    @check_lock
    def decrease(self) -> None:
        self._value -= 1
        if self._value < 0:
            self._value = 0
        ip = request.get_client_ip()
        if ip and not request.is_localhost():
            if ip in self._ips:
                self._ips[ip] -= 1
            if self._ips[ip] <= 0:
                del self._ips[ip]

    @check_lock
    def check(self, value: int) -> bool:
        return self._value > value or self._ips.get(request.get_client_ip(), 0) > 10


class Server:
    __slots__ = '_server'
    loading = ThreadSafeVariable(False)
    requests_count = Counter()

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
                                   app=self.__call__,
                                   request_handler=RequestHandler,
                                   threaded=self.max_threads_number > 1)
        # Set a timeout (1 seconds) to check for the stop event periodically
        self._server.timeout = 1
        run_event.set()

    def dispatch_request(self):
        if self.requests_count.check(self.max_threads_number):
            return controller.with_exception(TooManyRequests())
        attempt = 60
        while self.loading.value and attempt >= 0:
            time.sleep(1)
            attempt -= 1
        if self.loading.value:
            return controller.with_exception(ServiceUnavailable())
        else:
            adapter = controller.build_map_urls(modules).bind_to_environ(request.environ)
            try:
                request.endpoint, values = adapter.match()
            except NotFound:
                values = {}
            if request.endpoint:
                values.update(request.read_parameters())
                return controller(values)
            else:
                return controller.with_exception(NotFound())

    def __call__(self, environ, start_response) -> Any:
        classes.Request(environ, start_response)
        self.requests_count.increase()
        try:
            return self.dispatch_request()(environ, start_response)
        finally:
            self.requests_count.decrease()
            del local.request
