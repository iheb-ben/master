import traceback
from collections import defaultdict
from typing import Any, Dict, Tuple, Callable
from werkzeug.exceptions import NotFound, HTTPException, ServiceUnavailable
from werkzeug.routing import Map, Rule
from master.core.api import request
from master.core.exceptions import SimulateHTTPException
from master.core.service.http import route, html_route, Controller, Response, Endpoint
from master.core.service.static import StaticFilesMiddleware


# noinspection PyMethodMayBeStatic
class Base(Controller):
    def handle_error(self, error: Exception):
        request.error = error
        if request.httprequest.method == 'GET':
            status_code = 500
            if isinstance(error, HTTPException) or hasattr(error, 'code'):
                status_code = int(error.code)
            if status_code == 503:
                static_file_path = '/static/_/server_unavailable.html'
                content = StaticFilesMiddleware.get_full_path(request.application, static_file_path).open()
                response = Response(content, status=status_code)
            else:
                response = Response(template=f'base.page_{status_code}', status=status_code)
            if request.rule:
                response.content_type = request.rule.endpoint.content
            return response
        raise error

    def dispatch(self):
        if request.error and not request.httprequest.path.startswith('/_/simulate/'):
            raise request.error
        adapter = Map(
            rules=self.get_rules(),
            converters=self.get_converters(),
        ).bind_to_environ(environ=request.httprequest.environ)
        try:
            details: Tuple[Rule, Dict[str, Any]] = adapter.match(return_rule=True)
            request.rule, kwargs = details
            if not request.rule.endpoint:
                raise NotFound()
            response = request.rule.endpoint(**kwargs)
            request.env.flush()
            return response
        except Exception as error:
            error.traceback = traceback.format_stack()
            return self.handle_error(error)

    def get_converters(self):
        return self._compiled_converters

    def get_http_rules(self):
        if 'ir.http' in request.env and not request.httprequest.path.startswith('/_/simulate/'):
            return [Endpoint(
                func_name=endpoint.dispatch_url,
                auth=endpoint.is_public,
                content=endpoint.content_type,
                methods=endpoint.methods(),
                sitemap=endpoint.sitemap,
                rollback=True,
            ).as_rule(url=endpoint.url) for endpoint in request.env['ir.http'].sudo().search([])]
        return []

    def get_rules(self):
        return super().get_rules() + self.get_http_rules()

    @html_route('/_/simulate/<int:code>', rollback=False, sitemap=False)
    def _simulate_http_error(self, code):
        error = SimulateHTTPException('Simulate HTTP Exception')
        error.code = code
        raise error
