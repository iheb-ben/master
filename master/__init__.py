import traceback
from typing import Optional
from . import addons
from . import exceptions
from . import tools
from . import config
from . import core
from . import orm
from . import data

_logger = config.logging.get_logger(__name__)


def main():
    if config.parser.arguments.show_helper():
        exit(1)
    _logger.info(f"Master Password: {config.parser.arguments.configuration['master_password']}")
    config.configure_system()
    core.db.main()
    core.module.main()
    core.api.compile_classes()
    data.initialise_values()
    if config.parser.arguments.configuration['pipeline']:
        core.pipeline.main()
    else:
        core.server.main()
