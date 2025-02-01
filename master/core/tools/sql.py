def check_db_name(db_name: str):
    if not db_name:
        raise ValueError('Database name must not be empty')
    if len(db_name) > 50:
        raise ValueError('Database name is too long')
