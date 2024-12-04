# TODO: THIS FILE WILL BE UPDATED AND FIXED ACCORDINGLY
import threading
import time
from werkzeug.wrappers import Request, Response
from werkzeug.serving import make_server
from werkzeug.routing import Map, Rule
from werkzeug.local import Local, LocalProxy

from master.core import arguments
from master.core.threads import worker


class Server:
    __slots__ = ('_server', '_load', '_url_map')

    def __init__(self):
        self._server = None
        self._load = True
        self._url_map = Map([])

    def _load_endpoints(self):
        self._url_map = Map([
            Rule("/", endpoint="index"),
            Rule("/hello/<name>", endpoint="greet")
        ])

    @worker
    def run(self):
        if self._load:
            self._load_endpoints()
            self._load = False
        self._server.handle_request()

    def _start(self):
        self._server = make_server(host='localhost',
                                   port=arguments['port'],
                                   app=self.__call__,
                                   threaded=True)
        # Set a timeout to check for the stop event periodically
        self._server.timeout = 1

    def dispatch_request(self, request):
        while self._load:
            time.sleep(1)
        adapter = self._url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
            if endpoint == "index":
                return Response("Welcome to Werkzeug Server!", content_type="text/plain")
            elif endpoint == "greet":
                return Response(f"Hello, {values['name']}!", content_type="text/plain")
        except Exception as e:
            return Response(f"Error: {e}", status=404, content_type="text/plain")

    def __call__(self, environ, start_response):
        return self.dispatch_request(Request(environ))(environ, start_response)
