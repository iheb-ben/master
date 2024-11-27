import platform
from master import tools
from . import parser

# Initiate global values
arguments = parser.ArgumentParser().parse()
signature = {
    'mode': arguments['mode'],
    'node_type': arguments['node_type'],
    'os_name': platform.system(),
    'os_release': platform.release(),
    'os_version': platform.version(),
    'os_architecture': platform.architecture()[0],
    'public_ip': tools.ip.get_public_ip(raise_error=False),
    'private_ip': tools.ip.get_private_ip(raise_error=False),
    'mac_address': tools.ip.get_mac_address(),
    'python': platform.python_version(),
    'version': '1.0.0',
}

from . import logging
from . import threads
from . import pem
from . import jwt
from . import registry
from . import git
from . import modules
from . import orm
