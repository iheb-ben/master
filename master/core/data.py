from collections import defaultdict
from typing import Type, Any


class ClassHolder:
    def __init__(self):
        self.classes = defaultdict(list)
        self.core = list()

    def append(self, klass: Type[Any]):
        if not klass.__module__.startswith('master.addons.'):
            self.core.append(klass)
        else:
            module = klass.__module__.split('.')[2]
            self.classes[module].append(klass)
