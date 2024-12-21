from werkzeug.wrappers import Request as _Request
from . import enums
from . import paths
from . import methods
from . import norms
from . import generator
from . import system
from . import collection
from . import ip


def get_request_from_local_proxy() -> _Request:
    from master.core.endpoints import local
    try:
        current_request = getattr(local, 'request', None)
        if not current_request:
            raise AttributeError()
        return current_request
    except AttributeError:
        raise RuntimeError('Request is not available in the current context.')
