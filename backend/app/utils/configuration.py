import json
import secrets
from pathlib import Path
from typing import Optional
from app import config
import tempfile


class ConfigManager(dict):
    __slots__ = '_path'

    def __init__(self):
        super().__init__()
        self._path: Optional[Path] = None
        if config.FOLDER:
            file_path = Path(config.FOLDER) / 'config.json'
        else:
            file_path = Path(tempfile.gettempdir()) / 'master' / 'config.json'
        if not file_path.parent.is_dir():
            file_path.parent.mkdir()
        if not file_path.is_file():
            with file_path.open('w') as file:
                file.write('{}')
        else:
            self.update(json.load(file_path.open('r')))
        self._path = file_path

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if self._path:
            json.dump(self, self._path.open('w'))


config_store = ConfigManager()
if 'secret_key' not in config_store:
    config_store['secret_key'] = secrets.token_hex(32)
secret_key = config.SECRET_KEY or config_store['secret_key']
