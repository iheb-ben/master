from . import http
from . import static
from . import server
from master.core.database.connector import PoolManager


def main(pool: PoolManager):
    try:
        server.start_server(pool)
    finally:
        pool.shutdown()
