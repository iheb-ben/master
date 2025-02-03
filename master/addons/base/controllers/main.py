import traceback
from typing import Any, Dict, Tuple, Callable
from werkzeug.exceptions import NotFound, HTTPException, ServiceUnavailable
from werkzeug.routing import Map, Rule
from master.core.api import request
from master.core.service.http import route, html_route, Controller, Response, Endpoint
from master.core.service.static import STATIC_FOLDER


# noinspection PyMethodMayBeStatic
class Main(Controller):
    def dispatch(self):
        if request.error and not request.httprequest.path.startswith('/_/simulate/'):
            raise request.error
        adapter = Map(
            rules=self.get_rules(),
            converters=self.get_converters(),
        ).bind_to_environ(environ=request.httprequest.environ)
        try:
            details: Tuple[Rule, Dict[str, Any]] = adapter.match(return_rule=True)
            rule, kwargs = details
            if not rule.endpoint:
                raise NotFound()
            request.endpoint = rule.endpoint
            return rule.endpoint(**kwargs)
        except Exception as error:
            if request.httprequest.method == 'GET':
                status_code = 500
                if isinstance(error, HTTPException) or hasattr(error, 'code'):
                    status_code = error.code
                return Response(template=f'base.page_{int(status_code)}', status=status_code, context={
                    'error': error,
                })
            raise error

    def get_converters(self):
        return self.__converters__

    # noinspection PyBroadException
    def get_http_rules(self):
        current_list = []
        if request.httprequest.path.startswith('/_/simulate/'):
            return current_list
        try:
            for endpoint in request.env['ir.http'].sudo().search([]):
                current_list.append(Endpoint(
                    func_name=endpoint.dispatch_url,
                    auth=endpoint.is_public,
                    content=endpoint.content_type,
                    rollback=True,
                    sitemap=True,
                ).as_rule(url=endpoint.url))
        except Exception:
            pass
        return current_list

    def get_rules(self):
        current_list = []
        installed_addons = set(request.application.installed)
        for url, module_endpoint in self.__endpoints__.items():
            for module, endpoint in module_endpoint.items():
                if module not in installed_addons:
                    continue
                controller_method: Callable = getattr(self, endpoint.func_name, lambda *args, **kwargs: None)
                current_list.append(endpoint.wrap(func=controller_method).as_rule(url=url))
        return current_list + self.get_http_rules()

    @route('/')
    def homepage(self):
        return 'Home Page'

    @html_route('/_/simulate/<int:code>', rollback=False, sitemap=False)
    def _simulate_http_error(self, code):
        error = HTTPException(description='Simulate HTTP Exception')
        error.code = code
        if error.code == 503:
            return Response(
                response=STATIC_FOLDER.joinpath('server_unavailable.html').open(),
                status=error.code,
            )
        else:
            return Response(template=f'base.page_{error.code}', status=error.code, context={
                'error': error,
            })
