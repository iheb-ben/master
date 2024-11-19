from . import tree
from . import reader


def attach_modules(shutdown: bool = False):
    for configuration in reader.read_configurations(shutdown):
        print(configuration.to_dict())
