from werkzeug.exceptions import HTTPException


class SimulateHTTPException(HTTPException):
    def __init__(self, code: int):
        super().__init__('Simulate HTTP Exception')
        self.code = code
