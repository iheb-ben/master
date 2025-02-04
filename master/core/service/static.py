from collections import defaultdict
from pathlib import Path
from typing import Optional, Any, Dict, List, Tuple, Callable
from werkzeug.middleware.shared_data import SharedDataMiddleware
from master.core.tools.files import TEMP_STATIC_FOLDER
from master.core.tools.typing import SystemPath

STATIC_FOLDER = Path(__file__).parent.parent.parent.joinpath('static').absolute().resolve()


class StaticFilesMiddleware(SharedDataMiddleware):
    PREFIX = 'static'
    FOLDER_NAME = 'static'
    APP_EXPORTS: Dict[Any, List[Tuple[str, Callable]]] = defaultdict(list)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('exports', [])
        super().__init__(*args, **kwargs)

    @property
    def exports(self):
        if self.app:
            return self.APP_EXPORTS[self.app]
        return {}

    @exports.setter
    def exports(self, value):
        if self.app:
            self.APP_EXPORTS[self.app] = value

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

    def _fetch(self, path: SystemPath, base: Optional[str] = None):
        module_url = base and f'/{self.PREFIX}/{base}/' or f'/{self.PREFIX}/_/'
        return module_url, self.get_directory_loader(str(path))

    def _iterate_application_exports(self):
        yield self._fetch(STATIC_FOLDER)
        for module_name, system_path in self.app.paths.items():
            static_folder = system_path / self.FOLDER_NAME
            if static_folder.is_dir():
                yield self._fetch(static_folder, module_name)
        yield self._fetch(TEMP_STATIC_FOLDER, '_base')

    @classmethod
    def get_full_path(cls, app: Any, path: str) -> Path:
        for prefix, func in cls.APP_EXPORTS[app]:
            if path.startswith(prefix):
                relative_path = path[len(prefix):].lstrip('/')
                return Path(func(relative_path)[1]()[0].name)
        raise FileNotFoundError()
