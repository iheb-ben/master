from app import config
from . import auth
from . import user
if config.MODE == 'master':
    from . import ws
