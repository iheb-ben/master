import traceback
from . import addons
from . import exceptions
from . import tools
from . import config
from . import core
from . import orm
from . import data


def main():
    config.main()
    core.db.main()
    core.module.main()
    data.main()
    if config.arguments['pipeline']:
        core.pipeline.main()
    else:
        core.server.main()
