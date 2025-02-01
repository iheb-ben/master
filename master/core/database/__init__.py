from typing import Optional
from psycopg2.sql import Identifier, SQL
from . import cursor
from . import connector
from master.core.tools.config import environ
from master.core.tools.sql import check_db_name

BOT_ID = 1
PUBLIC_USER_ID = 2
SUPER_USER_ID = 3


def create_empty_database(db_name: str):
    check_db_name(db_name)
    current_pool = connector.main()
    with current_pool.get_cursor() as cr:
        query = SQL('SELECT datname FROM pg_database WHERE datname = %s')
        db_found = len([row[0] for row in cr.execute(sql=query, variables=db_name, fetch_type='all')]) > 0
    if not db_found:
        with current_pool.get_cursor() as cr:
            query = SQL("CREATE DATABASE {} ENCODING 'unicode'").format(Identifier(db_name))
            cr.execute(sql=query)
    current_pool.shutdown()


def main():
    create_empty_database(environ['PG_NAME'])
    return connector.main(True)
