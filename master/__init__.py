import traceback
from typing import Optional
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
    core.api.compile_classes()
    data.initialise_values()
    if config.arguments['pipeline']:
        core.pipeline.main()
    else:
        core.server.main()
