from pathlib import Path
from werkzeug.utils import secure_filename

from master import request
from master.api import route
from master.core.endpoints import Controller, generate_file_stream
from master.core.parser import PipelineMode


class Main(Controller):
    @route('/favicon.ico', methods='GET', mode=[PipelineMode.INSTANCE.value, PipelineMode.MANAGER.value])
    def favicon_icon(self):
        file_name = secure_filename(request.path.split('/')[-1])
        addon_file_path = f'base/static/src/description/{file_name}'
        file_path = Path('.').joinpath('master/addons').joinpath(addon_file_path).absolute().resolve()
        if file_path.is_file():
            generator = generate_file_stream(addon_file_path)
            return request.send_response(
                content=generator,
                mimetype='application/octet-stream',
                headers={'Content-Disposition': f'attachment; filename={file_name}'})
        return self.raise_exception(404, FileNotFoundError('File not found'))
