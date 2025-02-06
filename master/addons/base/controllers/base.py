import json
import traceback
from typing import Any, Dict, Tuple
from werkzeug.exceptions import NotFound, HTTPException
from werkzeug.routing import Map, Rule
from werkzeug.wrappers import Response as _Response
from master.core.api import request
from master.core.service.http import Controller, Response, Endpoint
from master.core.service.static import StaticFilesMiddleware


def _check_ect(*content_types: str):
    if data := (request.rule or ''):
        data = data.endpoint.content or ''
    return not data or any(value in data for value in content_types)


# noinspection PyMethodMayBeStatic
class Base(Controller):
    def _handle_error(self, error: Exception):
        request.error = error
        status_code = 500
        if isinstance(error, HTTPException) or hasattr(error, 'code'):
            status_code = int(error.code)
        if _check_ect('text/html', 'text/xhtml') and request.httprequest.accept_mimetypes.accept_html:
            if status_code == 503:
                static_file_path = '/static/_/server_unavailable.html'
                content = StaticFilesMiddleware.get_full_path(static_file_path).open()
                return Response(content, status=status_code, content_type='text/html')
            else:
                return Response(template=f'base.page_{status_code}', status=status_code)
        elif _check_ect('application/json') and request.httprequest.accept_mimetypes.accept_json:
            return Response(
                response=json.dumps({
                    'error': str(request.error),
                    'traceback': request.error.traceback,
                }),
                status=status_code,
                content_type='application/json',
            )
        raise error

    def _middleware_before_request(self):
        return None

    def _middleware_after_request(self, response: Any):
        return response

    def _middleware(self, *args, **kwargs):
        def _execute():
            try:
                return request.rule.endpoint.func_name(*args, **kwargs)
            except Exception:
                if request.rule.endpoint.rollback:
                    request.env.clear()
                raise

        if request.rule.endpoint.rollback:
            with request.env.cursor.with_savepoint():
                if before := self._middleware_before_request():
                    return before
                return self._middleware_after_request(_execute())
        else:
            if before := self._middleware_before_request():
                return before
            return self._middleware_after_request(_execute())

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

    def dispatch(self):
        try:
            if request.error:
                return self._handle_error(request.error)
            adapter = Map(
                rules=self.get_rules(),
                converters=self.get_converters(),
            ).bind_to_environ(environ=request.httprequest.environ)
            details: Tuple[Rule, Dict[str, Any]] = adapter.match(return_rule=True)
            request.rule, kwargs = details
            if not request.rule.endpoint:
                raise NotFound()
            response = self._middleware(**kwargs)
            request.env.flush()
            return response
        except Exception as error:
            error.traceback = traceback.format_exception(error)
            return self._handle_error(error)

    def __call__(self):
        response: Any = self.dispatch()
        accept_mimetypes, request_rule, status = request.httprequest.accept_mimetypes, request.rule, 200
        content_type: Optional[str] = request_rule and request_rule.endpoint.content or None
        response = response or Response(status=status, content_type=content_type)
        if response:
            if isinstance(response, _Response):
                if 'text/plain' in response.content_type and content_type:
                    response.content_type = content_type
                return response
            if isinstance(response, tuple):
                response, current_status = response
                status = current_status or status
            if isinstance(response, dict):
                response = json.dumps(response)
                if not content_type and accept_mimetypes.accept_json:
                    content_type = 'application/json'
            if not content_type:
                if isinstance(response, str) and accept_mimetypes.accept_html and _check_ect('text/html', 'text/xhtml'):
                    content_type = 'text/html'
                elif isinstance(response, str) and accept_mimetypes.accept_xml and _check_ect('application/xml'):
                    content_type = 'application/xml'
            if not isinstance(response, _Response):
                response = Response(response=response, status=status, content_type=content_type)
        return response
