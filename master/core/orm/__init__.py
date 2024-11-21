from typing import Optional, Type
import psycopg2
from master.config.logging import get_logger
from master.config.parser import arguments
from master.core.api import Class
from . import models
from . import fields

TableType = Type[models.TransientModel | models.Model]
_logger = get_logger(__name__)


class DBStructureManager(Class):
    __meta_path__ = 'master.core.DBStructureManager'
    __value_path__ = 'master.db_structure_manager'
    __slots__ = ('connection', 'grouped')

    def __init__(self, connection: 'psycopg2.connection'):
        """Initialize the database tables."""
        self.connection = connection
        self.grouped = {}
        query = """
        SELECT 
            t.tablename AS table_name,
            c.column_name,
            c.data_type,
            CASE 
                WHEN t.schemaname = 'pg_temp' THEN 'Yes'
                ELSE 'No'
            END AS is_temporary
        FROM 
            pg_tables t
        JOIN 
            information_schema.columns c 
        ON 
            t.tablename = c.table_name
        WHERE 
            t.schemaname NOT IN ('pg_catalog', 'information_schema')
        ORDER BY 
            t.tablename, c.ordinal_position;
        """
        with connection.cursor() as cursor:
            cursor.execute(query)
            for table_name, column_name, data_type, is_temporary in cursor.fetchall():
                if table_name not in self.grouped:
                    self.grouped[table_name] = {
                        'is_temporary': is_temporary,
                        'columns': [],
                    }
                self.grouped[table_name]['columns'].append({
                    'column_name': column_name,
                    'data_type': data_type,
                })

    def define_table(self, Table: TableType):
        """
        Define a table dynamically based on ORM class.
        :param Table: ORM Class.
        """
        table_name = getattr(Table, '_name', None)
        if not table_name:
            return False
        is_temporary = not issubclass(Table, models.Model)
        if table_name not in self.grouped:
            self.grouped[table_name] = {
                'is_temporary': is_temporary,
                'columns': [],
            }
            for column_name in dir(Table):
                field = getattr(Table, column_name)
                if not isinstance(field, fields.Field):
                    continue
                data_type = field.type()
                if not data_type:
                    continue
                self.grouped[table_name]['columns'].append({
                    'column_name': column_name,
                    'data_type': data_type,
                })
        else:
            self.grouped[table_name]['is_temporary'] = is_temporary
            for column_name in dir(Table):
                field = getattr(Table, column_name)
                if not isinstance(field, fields.Field):
                    continue
                data_type = field.type()
                if not data_type:
                    continue
                self.grouped[table_name]['columns'].append({
                    'column_name': column_name,
                    'data_type': data_type,
                })
        return True
