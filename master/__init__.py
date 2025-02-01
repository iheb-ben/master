from pathlib import Path
from . import addons
from . import core


def main():
    environ = core.tools.config.main()
    if environ['HELP_MODE']:
        return core.tools.config.parser.print_help()
    base_addons = str(Path(addons.__file__).parent)
    if base_addons not in environ['ADDONS_PATHS']:
        environ['ADDONS_PATHS'].insert(0, base_addons)
    core.main()
