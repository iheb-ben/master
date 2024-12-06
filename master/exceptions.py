class Error(Exception):
    pass


class HTTPError(Error):
    pass


class AccessDeniedError(HTTPError):
    pass


class DatabaseError(Error):
    pass


class DatabaseAccessError(DatabaseError):
    pass


class DatabaseSessionError(DatabaseError):
    pass


class DatabaseRoleError(DatabaseError):
    pass
