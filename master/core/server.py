import time
from werkzeug.wrappers import Response
from werkzeug.serving import make_server

from master.core import arguments
from master.core.modules import default_installed_modules
from master.core.registry import ClassManager
from master.core.threads import worker, ThreadManager

modules = []
classes = None


class Server:
    __slots__ = '_server'
    loading = False

    def __init__(self):
        self._server = None

    @worker
    def run(self):
        self._server.handle_request()

    def _start(self):
        global modules, classes
        modules = default_installed_modules()
        classes = ClassManager(modules)
        import master
        master.postgres_manager = classes.PostgresManager(arguments['db_name'])
        if arguments['db_mongo']:
            master.mongo_db_manager = classes.MongoDBManager(arguments['db_name'])
        self._server = make_server(host='localhost',
                                   port=arguments['port'],
                                   app=self.__call__,
                                   threaded=True)
        # Set a timeout (2 seconds) to check for the stop event periodically
        self._server.timeout = 2
        ThreadManager.allow.set()

    def dispatch_request(self, request):
        attempt = 60
        while self.loading and attempt >= 0:
            time.sleep(1)
            attempt -= 1
        if self.loading:
            return Response("Server is busy!", status=500, content_type="text/plain")
        controller = classes.Controller()
        adapter = controller.build_urls(modules).bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
            return getattr(controller, endpoint)(values)
        except Exception as e:
            return Response(f"Error: {e}", status=404, content_type="text/plain")

    def __call__(self, environ, start_response):
        return self.dispatch_request(classes.Request(environ))(environ, start_response)
