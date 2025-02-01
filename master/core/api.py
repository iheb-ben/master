from typing import Any, Dict
from master.core.database.cursor import Cursor


class Environment:
    def __init__(self, cursor: Cursor, registry: Any, context: Dict[str, Any]):
        self._registry = registry
        self.cr = cursor
        self.context = context
