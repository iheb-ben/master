import traceback
from typing import Any, Dict, Tuple, Callable
from werkzeug.exceptions import NotFound, HTTPException
from werkzeug.routing import Map, Rule
from master.core.api import request
from master.core.service.http import route, Controller, Response, Endpoint


class Main(Controller):
    def dispatch(self):
        adapter = Map(
            rules=self.get_rules(),
            converters=self.get_converters(),
        ).bind_to_environ(environ=request.httprequest.environ)
        try:
            details: Tuple[Rule, Dict[str, Any]] = adapter.match(return_rule=True)
            rule, kwargs = details
            if not rule.endpoint:
                raise NotFound()
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

    def get_rules(self):
        current_list = []
        installed_addons = set(request.application.installed)
        for url, module_endpoint in self.__endpoints__.items():
            for module, endpoint in module_endpoint.items():
                if module not in installed_addons:
                    continue
                controller_method: Callable = getattr(self, endpoint.func_name, lambda *args, **kwargs: None)
                current_list.append(endpoint.wrap(func=controller_method).as_rule(url=url))
        # noinspection PyBroadException
        try:
            for endpoint in request.env['ir.http'].sudo().search([]):
                current_list.append(Endpoint(func_name=endpoint.dispatch_url, auth=endpoint.is_public, rollback=True).as_rule(url=endpoint.url))
        except Exception:
            pass
        return current_list

    @route('/')
    def homepage(self):
        return 'Home Page'
