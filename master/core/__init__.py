from . import tools
from . import database
from . import api
from . import module
from . import service


def main():
    pool = database.main()
    service.main(pool)
