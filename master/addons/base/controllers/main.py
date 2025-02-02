import traceback
from typing import Any, Dict, Tuple
from werkzeug import wrappers
from werkzeug.exceptions import NotFound, HTTPException
from werkzeug.routing import Map, Rule
from master.core.api import request
from master.core.service.http import route, Controller, Response, Endpoint


class Main(Controller):
    def dispatch(self):
        adapter = Map(
            rules=self.url_map(),
            converters=self.__converters__,
        ).bind_to_environ(environ=request.httprequest.environ)
        try:
            details: Tuple[Rule, Dict[str, Any]] = adapter.match(return_rule=True)
            rule, kwargs = details
            if not rule.endpoint:
                raise NotFound()
            if isinstance(rule.endpoint, tuple):
                method_name, endpoint = rule.endpoint
                controller_func = Endpoint.wrap(getattr(self, method_name))
                if endpoint.rollback:
                    with request.env.cursor.with_savepoint():
                        return controller_func(**kwargs)
                return controller_func(**kwargs)
            elif callable(rule.endpoint):
                return Endpoint.wrap(rule.endpoint)()
            else:
                raise RuntimeError('Weird endpoint definition')
        except Exception as error:
            if request.httprequest.method == 'GET':
                status_code = 500
                if isinstance(error, HTTPException) or hasattr(error, 'code'):
                    status_code = error.code
                return Response(template=f'base.page_{int(status_code)}', status=status_code, context={
                    'error': error,
                })
            raise error

    def url_map(self):
        current_list = []
        for module in request.application.installed:
            for name, endpoints in self.__endpoints__.items():
                for endpoint in endpoints:
                    if endpoint.module != module:
                        continue
                    current_list.append(Rule(string=endpoint.url, endpoint=(name, endpoint)))
        # noinspection PyBroadException
        try:
            for endpoint in request.env['ir.http'].search([]):
                current_list.append(Rule(string=endpoint.url, endpoint=endpoint.dispatch_url))
        except Exception:
            pass
        return current_list
