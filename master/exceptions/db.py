from master.exceptions.basic import Error


class DatabaseError(Error):
    pass


class DatabaseSessionError(DatabaseError):
    pass


class DatabaseAccessError(DatabaseError):
    pass


class DatabaseRoleError(DatabaseError):
    pass
