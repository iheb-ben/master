from io import BytesIO
import magic
import json
import traceback
from typing import Any
from magic import Magic, MagicException
from werkzeug.exceptions import NotFound, HTTPException
from werkzeug.routing import Map
from werkzeug.wrappers import Response as _Response
from master.core.api import request
from master.core.service.http import Controller, Response, Endpoint
from master.core.service.static import StaticFilesMiddleware


def _check_ect(*content_types: str):
    if data := (request.rule or ''):
        data = data.endpoint.content or ''
    return not data or any(value in data for value in content_types)


def _find_content_type(first_bytes):
    try:
        return Magic(mime=True).from_buffer(first_bytes)
    except MagicException:
        return None


# noinspection PyMethodMayBeStatic
class Base(Controller):
    def _update_response_context(self, response: Response):
        for key, item in request.context.items():
            response.context.setdefault(key, item)
        response.context.setdefault('error', request.error)
        response.context['request'] = request

    def _render(self, response: Response):
        mode_name = 'ir.qweb'
        if mode_name in request.env:
            if qweb_id := request.env[mode_name].sudo().search([('xml_id', '=', response.template)], limit=1):
                response.data = qweb_id.render(response.context).encode('utf-8')
        response.content_type = 'text/html; charset=utf-8'

    def _handle_error_html_503(self):
        content = StaticFilesMiddleware.get_full_path('/static/_/server_unavailable.html').open()
        return Response(content, status=request.error.code, content_type='text/html')

    def _handle_error_html(self):
        return Response(template=f'base.page_{request.error.code}', status=request.error.code, content_type='text/html')

    def _handle_error_json(self):
        return Response(response=json.dumps({
            'error': str(request.error),
            'traceback': request.error.traceback,
        }), status=request.error.code, content_type='application/json')

    def _handle_error(self, error: Exception, status_code: int = 500):
        request.error, func_name = error, None
        if isinstance(error, HTTPException) or hasattr(error, 'code'):
            status_code = int(error.code)
        if _check_ect('text/html', 'application/xhtml+xml') and request.httprequest.accept_mimetypes.accept_html:
            func_name = 'html'
        elif _check_ect('application/xhtml+xml', 'application/xml') and request.httprequest.accept_mimetypes.accept_xhtml:
            func_name = 'xml'
        elif _check_ect('application/json') and request.httprequest.accept_mimetypes.accept_json:
            func_name = 'json'
        if func_name:
            for func_name in (f'_handle_error_{func_name}_{status_code}', f'_handle_error_{func_name}'):
                if not hasattr(self, func_name):
                    continue
                return self.__getattribute__(func_name)()
        raise error

    def _middleware_before_request(self):
        return None

    def _middleware_after_request(self, response: Any):
        return response

    def _authorize(self):
        pass

    def _middleware(self, *args, **kwargs):
        def _execute():
            try:
                if request.rule.endpoint.auth:
                    if response := self._authorize():
                        return response
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

    def _get_converters(self):
        return self._compiled_converters

    def _get_http_rules(self):
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

    def _get_rules(self):
        return super().get_rules() + self._get_http_rules()

    def _bind_to_environ(self):
        return Map(
            rules=self._get_rules(),
            converters=self._get_converters(),
        ).bind_to_environ(environ=request.httprequest.environ)

    def _dispatch(self):
        if request.error:
            return self._handle_error(request.error)
        try:
            request.rule, kwargs = self._bind_to_environ().match(return_rule=True)
            response = self._middleware(**kwargs)
            request.env.flush()
            return response
        except Exception as error:
            error.traceback = traceback.format_exception(error)
            return self._handle_error(error)

    def _build_response(self) -> _Response:
        response: Any = self._dispatch()
        accept_mimetypes, request_rule, status = request.httprequest.accept_mimetypes, request.rule, 200
        content_type: Optional[str] = request_rule and request_rule.endpoint.content or None
        response = response or Response(status=status, content_type=content_type)
        if isinstance(response, _Response):
            if content_type:
                response.content_type = content_type
            return response
        if isinstance(response, tuple):
            response, current_status = response
            status = current_status or status
        if isinstance(response, dict) or isinstance(response, list):
            response = json.dumps(response)
            if not content_type and accept_mimetypes.accept_json:
                content_type = 'application/json'
        if not content_type:
            if isinstance(response, str) and accept_mimetypes.accept_html:
                content_type = 'text/html'
            elif isinstance(response, str) and accept_mimetypes.accept_xml:
                content_type = 'application/xml'
            elif isinstance(response, BytesIO):
                content_type = _find_content_type(response.read(2048)) or 'application/octet-stream'
                response.seek(0)
            elif isinstance(response, bytes):
                content_type = _find_content_type(response[:2048]) or 'application/octet-stream'
        return Response(response=response, status=status, content_type=content_type)

    def dispatch(self):
        response: _Response = self._build_response()
        if isinstance(response, Response) and response.template:
            self._update_response_context(response)
            self._render(response)
        return response
