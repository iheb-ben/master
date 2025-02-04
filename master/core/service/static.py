from os import PathLike
from pathlib import Path
from typing import Union, Optional
from werkzeug.middleware.shared_data import SharedDataMiddleware

STATIC_FOLDER = Path(__file__).parent.parent.parent.joinpath('static').absolute().resolve()


class StaticFilesMiddleware(SharedDataMiddleware):
    PREFIX = 'static'
    FOLDER_NAME = 'static'

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('exports', [])
        super().__init__(*args, **kwargs)

    @property
    def stop_event(self):
        return self.app.stop_event

    @property
    def reload_event(self):
        return self.app.reload_event

    def reload(self):
        self.app.reload()
        self.exports.clear()
        for static in self._iterate_application_exports():
            self.exports.append(static)

    def _fetch(self, path: Union[Path, PathLike, str], base: Optional[str] = None):
        module_url = base and f'/{self.PREFIX}/{base}/' or f'/{self.PREFIX}/_/'
        return module_url, self.get_directory_loader(str(path))

    def _iterate_application_exports(self):
        yield self._fetch(STATIC_FOLDER)
        for module_name, system_path in self.app.paths.items():
            static_folder = system_path / self.FOLDER_NAME
            if static_folder.is_dir():
                yield self._fetch(static_folder, module_name)
