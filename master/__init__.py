import traceback
import sys
from . import tools
from . import addons
from . import api
from . import core


def main():
    if core.arguments['help']:
        core.parser.ArgumentParser().help()
        sys.exit(1)
