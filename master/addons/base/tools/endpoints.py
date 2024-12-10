from typing import Dict, Any, Optional
from master.core.endpoints import Request as _Request, Response as _Response


class Request(_Request):
    def render(self, template_xml_id: str, context: Optional[Dict[str, Any]] = None):
        response = self.send_response(status=200, mimetype='text/html')
        response.render_template = template_xml_id
        response.template_context = context or {}
        return response


class Response(_Response):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.render_template: Optional[str] = None
        self.template_context: Optional[Dict[str, Any]] = None

    def render(self):
        if self.render_template and self.content_type == 'text/html':
            context = self.template_context or {}
            self.data = b''

    def __call__(self, *args, **kwargs):
        self.render()
        return super().__call__(*args, **kwargs)
