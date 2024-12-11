from pathlib import Path
from werkzeug.exceptions import NotFound, BadRequest
from werkzeug.utils import secure_filename

from master import request
from master.api import route
from master.core.endpoints import Controller, generate_file_stream
from master.core.modules import configurations, base_addon
from master.core.parser import PipelineMode


# noinspection PyMethodMayBeStatic
class Main(Controller):
    def _return_resource(self, file_path: str):
        path = Path(file_path)
        if path.is_file():
            return request.send_response(
                content=generate_file_stream(file_path),
                headers={'Content-Disposition': f'attachment;filename={secure_filename(path.name)}'})
        raise NotFound()

    @route('/favicon.ico', methods='GET', mode=[PipelineMode.INSTANCE.value, PipelineMode.MANAGER.value], content='application/octet-stream')
    def favicon(self):
        return self._return_resource(str(configurations[base_addon].path / 'static/src/description/favicon.ico'))

    @route('/static/<path:file_path>', methods='GET', mode=[PipelineMode.INSTANCE.value, PipelineMode.MANAGER.value], content='application/octet-stream')
    def static_files(self, file_path: str):
        file_path_elements = file_path and file_path.split('/') or []
        if len(file_path_elements) < 2:
            raise BadRequest()
        addon_name = file_path_elements[0]
        if addon_name not in configurations:
            raise NotFound()
        file_path = configurations[addon_name].path / 'static' / '/'.join(file_path_elements[1:])
        return self._return_resource(str(file_path))
