from typing import Dict, Any

from typing_extensions import Optional

from master.core.endpoints import Request as _Request


class Request(_Request):
    def render(self, template_xml_id: str, context: Optional[Dict[str, Any]] = None):
        response = self.send_response(status=200, mimetype='text/html')
        response.render_template = template_xml_id
        response.template_context = context or {}
        return response


from . import controllers
