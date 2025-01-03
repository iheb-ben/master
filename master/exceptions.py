class Error(Exception):
    pass


class DatabaseError(Error):
    pass


class DatabaseAccessError(DatabaseError):
    pass


class DatabaseSessionError(DatabaseError):
    pass


class DatabaseRoleError(DatabaseError):
    pass
