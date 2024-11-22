import traceback
from . import addons
from . import exceptions
from . import tools
from . import config
from . import core
from . import orm
from . import common


def main():
    config.main()
    core.db.main()
    core.module.main()
    common.main()
    if config.arguments['pipeline']:
        core.pipeline.main()
    else:
        core.server.main()
