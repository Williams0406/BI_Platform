from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from .base import BaseConnector
from .exceptions import ConnectorConnectionError, ConnectorQueryError
from .types import ColumnInfo, ForeignKeyInfo


POSTGRES_TYPE_MAP = {
    "smallint": "INTEGER",
    "integer": "INTEGER",
    "bigint": "BIGINT",
    "numeric": "DECIMAL",
    "decimal": "DECIMAL",
    "real": "FLOAT",
    "double precision": "FLOAT",
    "boolean": "BOOLEAN",
    "character varying": "STRING",
    "varchar": "STRING",
    "character": "STRING",
    "char": "STRING",
    "text": "TEXT",
    "date": "DATE",
    "timestamp without time zone": "DATETIME",
    "timestamp with time zone": "DATETIME_TZ",
    "time without time zone": "TIME",
    "uuid": "UUID",
    "json": "JSON",
    "jsonb": "JSON",
    "bytea": "BINARY",
}


class PostgreSQLConnector(BaseConnector):
    engine = "POSTGRESQL"
    required_config_fields = ("host", "database", "user")

    def _connection_kwargs(self):
        return {
            "host": self.config["host"],
            "port": int(self.config.get("port") or 5432),
            "dbname": self.config["database"],
            "user": self.config["user"],
            "password": self.config.get("password", ""),
            "connect_timeout": int(self.config.get("connect_timeout") or 5),
            "sslmode": self.config.get("sslmode", "prefer"),
            "row_factory": dict_row,
        }

    @contextmanager
    def connection(self):
        try:
            with psycopg.connect(**self._connection_kwargs()) as conn:
                yield conn
        except Exception as exc:
            raise ConnectorConnectionError(str(exc)) from exc

    def quote_identifier(self, identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'

    def test_connection(self) -> dict[str, Any]:
        try:
            with self.connection() as conn, conn.cursor() as cursor:
                cursor.execute(
                    "SELECT current_database() AS database, "
                    "current_user AS db_user, version() AS version"
                )
                row = cursor.fetchone()
                return {
                    "ok": True,
                    "engine": self.engine,
                    "database": row["database"],
                    "db_user": row["db_user"],
                    "version": row["version"],
                }
        except Exception as exc:
            if isinstance(exc, ConnectorConnectionError):
                raise
            raise ConnectorConnectionError(str(exc)) from exc

    def list_schemas(self) -> list[str]:
        query = """
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
              AND schema_name NOT LIKE 'pg_toast%'
              AND schema_name NOT LIKE 'pg_temp_%'
            ORDER BY schema_name
        """
        with self.connection() as conn, conn.cursor() as cursor:
            cursor.execute(query)
            return [row["schema_name"] for row in cursor.fetchall()]

    def list_tables(self, schemas=None) -> list[dict[str, Any]]:
        query = """
            SELECT
                table_schema,
                table_name,
                CASE
                    WHEN table_type = 'VIEW' THEN 'VIEW'
                    ELSE 'TABLE'
                END AS normalized_type
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
              AND table_schema NOT LIKE 'pg_toast%'
              AND table_schema NOT LIKE 'pg_temp_%'
        """
        params = []
        if schemas:
            query += " AND table_schema = ANY(%s)"
            params.append(schemas)
        query += " ORDER BY table_schema, table_name"

        with self.connection() as conn, conn.cursor() as cursor:
            cursor.execute(query, params)
            return [
                {
                    "schema": row["table_schema"],
                    "name": row["table_name"],
                    "table_type": row["normalized_type"],
                }
                for row in cursor.fetchall()
            ]

    def get_columns(self, schema: str, table: str) -> list[ColumnInfo]:
        query = """
            SELECT
                column_name,
                data_type,
                udt_name,
                is_nullable,
                ordinal_position,
                column_default,
                character_maximum_length,
                numeric_precision,
                numeric_scale,
                is_identity
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """
        with self.connection() as conn, conn.cursor() as cursor:
            cursor.execute(query, [schema, table])
            rows = cursor.fetchall()

        return [
            ColumnInfo(
                name=row["column_name"],
                data_type=POSTGRES_TYPE_MAP.get(
                    row["data_type"],
                    POSTGRES_TYPE_MAP.get(row["udt_name"], "OTHER"),
                ),
                native_type=row["data_type"],
                nullable=row["is_nullable"] == "YES",
                ordinal_position=row["ordinal_position"],
                default=row["column_default"],
                max_length=row["character_maximum_length"],
                numeric_precision=row["numeric_precision"],
                numeric_scale=row["numeric_scale"],
                is_identity=row["is_identity"] == "YES",
            )
            for row in rows
        ]

    def get_primary_key(self, schema: str, table: str) -> list[str]:
        query = """
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.constraint_schema = kcu.constraint_schema
             AND tc.table_name = kcu.table_name
            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_schema = %s
              AND tc.table_name = %s
            ORDER BY kcu.ordinal_position
        """
        with self.connection() as conn, conn.cursor() as cursor:
            cursor.execute(query, [schema, table])
            return [row["column_name"] for row in cursor.fetchall()]

    def get_foreign_keys(self, schema: str, table: str) -> list[ForeignKeyInfo]:
        query = """
            SELECT
                tc.constraint_name,
                kcu.column_name AS source_column,
                ccu.table_schema AS target_schema,
                ccu.table_name AS target_table,
                ccu.column_name AS target_column,
                kcu.ordinal_position
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.constraint_schema = kcu.constraint_schema
            JOIN information_schema.constraint_column_usage ccu
              ON ccu.constraint_name = tc.constraint_name
             AND ccu.constraint_schema = tc.constraint_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = %s
              AND tc.table_name = %s
            ORDER BY tc.constraint_name, kcu.ordinal_position
        """
        with self.connection() as conn, conn.cursor() as cursor:
            cursor.execute(query, [schema, table])
            rows = cursor.fetchall()

        grouped = {}
        for row in rows:
            key = row["constraint_name"]
            item = grouped.setdefault(
                key,
                {
                    "source_columns": [],
                    "target_columns": [],
                    "target_schema": row["target_schema"],
                    "target_table": row["target_table"],
                },
            )
            item["source_columns"].append(row["source_column"])
            item["target_columns"].append(row["target_column"])

        return [
            ForeignKeyInfo(
                name=name,
                source_schema=schema,
                source_table=table,
                source_columns=data["source_columns"],
                target_schema=data["target_schema"],
                target_table=data["target_table"],
                target_columns=data["target_columns"],
            )
            for name, data in grouped.items()
        ]

    def read_page(self, schema, table, columns=None, limit=100, offset=0, cursor_field=None, cursor_gt=None):
        limit = self.normalize_limit(limit)
        offset = self.normalize_offset(offset)

        selected = (
            sql.SQL(", ").join(sql.Identifier(column) for column in columns)
            if columns
            else sql.SQL("*")
        )
        query = sql.SQL("SELECT {columns} FROM {schema}.{table}").format(
            columns=selected,
            schema=sql.Identifier(schema),
            table=sql.Identifier(table),
        )
        params = []
        if cursor_field and cursor_gt is not None:
            query += sql.SQL(" WHERE {cursor_field} > %s").format(cursor_field=sql.Identifier(cursor_field))
            params.append(cursor_gt)
            query += sql.SQL(" ORDER BY {cursor_field}").format(cursor_field=sql.Identifier(cursor_field))
        query += sql.SQL(" LIMIT %s OFFSET %s")
        params.extend([limit, offset])

        try:
            with self.connection() as conn, conn.cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()
                return {
                    "rows": rows,
                    "limit": limit,
                    "offset": offset,
                    "returned": len(rows),
                }
        except Exception as exc:
            raise ConnectorQueryError(str(exc)) from exc
    def execute_select(self, query, params=None):
        try:
            with self.connection() as conn, conn.cursor() as cursor:
                cursor.execute(query, params or [])
                rows = cursor.fetchall()
                return {"rows": rows, "returned": len(rows)}
        except Exception as exc:
            raise ConnectorQueryError(str(exc)) from exc

