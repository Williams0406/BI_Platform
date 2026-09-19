from contextlib import contextmanager
from typing import Any

import pyodbc

from .base import BaseConnector
from .exceptions import ConnectorConnectionError, ConnectorQueryError
from .types import ColumnInfo, ForeignKeyInfo


SQLSERVER_TYPE_MAP = {
    "tinyint": "INTEGER",
    "smallint": "INTEGER",
    "int": "INTEGER",
    "bigint": "BIGINT",
    "decimal": "DECIMAL",
    "numeric": "DECIMAL",
    "money": "DECIMAL",
    "smallmoney": "DECIMAL",
    "float": "FLOAT",
    "real": "FLOAT",
    "bit": "BOOLEAN",
    "char": "STRING",
    "nchar": "STRING",
    "varchar": "STRING",
    "nvarchar": "STRING",
    "text": "TEXT",
    "ntext": "TEXT",
    "date": "DATE",
    "datetime": "DATETIME",
    "datetime2": "DATETIME",
    "smalldatetime": "DATETIME",
    "datetimeoffset": "DATETIME_TZ",
    "time": "TIME",
    "uniqueidentifier": "UUID",
    "binary": "BINARY",
    "varbinary": "BINARY",
    "image": "BINARY",
}


class SQLServerConnector(BaseConnector):
    engine = "SQLSERVER"
    required_config_fields = ("server", "database")

    def _connection_string(self):
        driver = self.config.get("driver", "ODBC Driver 18 for SQL Server")
        parts = [
            f"DRIVER={{{driver}}}",
            f"SERVER={self.config['server']}",
            f"DATABASE={self.config['database']}",
        ]

        if self.config.get("trusted_connection"):
            parts.append("Trusted_Connection=yes")
        else:
            if not self.config.get("user"):
                raise ConnectorConnectionError(
                    "Se requiere 'user' si trusted_connection=false."
                )
            parts.extend(
                [
                    f"UID={self.config['user']}",
                    f"PWD={self.config.get('password', '')}",
                ]
            )

        parts.append(
            f"Encrypt={'yes' if self.config.get('encrypt', True) else 'no'}"
        )
        parts.append(
            "TrustServerCertificate="
            + ("yes" if self.config.get("trust_server_certificate", False) else "no")
        )
        parts.append(
            f"Connection Timeout={int(self.config.get('connect_timeout') or 5)}"
        )
        return ";".join(parts) + ";"

    @contextmanager
    def connection(self):
        try:
            conn = pyodbc.connect(self._connection_string(), autocommit=False)
            try:
                yield conn
            finally:
                conn.close()
        except Exception as exc:
            raise ConnectorConnectionError(str(exc)) from exc

    def quote_identifier(self, identifier: str) -> str:
        return "[" + identifier.replace("]", "]]") + "]"

    @staticmethod
    def _row_to_dict(cursor, row):
        columns = [column[0] for column in cursor.description]
        return dict(zip(columns, row))

    def test_connection(self) -> dict[str, Any]:
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DB_NAME() AS [database], "
                "SUSER_SNAME() AS [db_user], "
                "@@VERSION AS [version]"
            )
            row = self._row_to_dict(cursor, cursor.fetchone())
            return {
                "ok": True,
                "engine": self.engine,
                "database": row["database"],
                "db_user": row["db_user"],
                "version": row["version"],
            }

    def list_schemas(self) -> list[str]:
        query = """
            SELECT name
            FROM sys.schemas
            WHERE name NOT IN (
                'sys', 'INFORMATION_SCHEMA', 'guest', 'db_owner',
                'db_accessadmin', 'db_securityadmin', 'db_ddladmin',
                'db_backupoperator', 'db_datareader', 'db_datawriter',
                'db_denydatareader', 'db_denydatawriter'
            )
            ORDER BY name
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            return [row[0] for row in cursor.fetchall()]

    def list_tables(self, schemas=None) -> list[dict[str, Any]]:
        query = """
            SELECT
                s.name AS schema_name,
                o.name AS object_name,
                CASE WHEN o.type = 'V' THEN 'VIEW' ELSE 'TABLE' END AS table_type
            FROM sys.objects o
            JOIN sys.schemas s ON s.schema_id = o.schema_id
            WHERE o.type IN ('U', 'V')
              AND o.is_ms_shipped = 0
        """
        params = []
        if schemas:
            placeholders = ",".join("?" for _ in schemas)
            query += f" AND s.name IN ({placeholders})"
            params.extend(schemas)
        query += " ORDER BY s.name, o.name"

        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [
                {
                    "schema": row[0],
                    "name": row[1],
                    "table_type": row[2],
                }
                for row in cursor.fetchall()
            ]

    def get_columns(self, schema: str, table: str) -> list[ColumnInfo]:
        query = """
            SELECT
                c.COLUMN_NAME,
                c.DATA_TYPE,
                c.IS_NULLABLE,
                c.ORDINAL_POSITION,
                c.COLUMN_DEFAULT,
                c.CHARACTER_MAXIMUM_LENGTH,
                c.NUMERIC_PRECISION,
                c.NUMERIC_SCALE,
                COLUMNPROPERTY(
                    OBJECT_ID(QUOTENAME(c.TABLE_SCHEMA) + '.' + QUOTENAME(c.TABLE_NAME)),
                    c.COLUMN_NAME,
                    'IsIdentity'
                ) AS IS_IDENTITY
            FROM INFORMATION_SCHEMA.COLUMNS c
            WHERE c.TABLE_SCHEMA = ? AND c.TABLE_NAME = ?
            ORDER BY c.ORDINAL_POSITION
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, [schema, table])
            rows = cursor.fetchall()

        return [
            ColumnInfo(
                name=row[0],
                data_type=SQLSERVER_TYPE_MAP.get(str(row[1]).lower(), "OTHER"),
                native_type=str(row[1]).lower(),
                nullable=row[2] == "YES",
                ordinal_position=row[3],
                default=row[4],
                max_length=row[5],
                numeric_precision=row[6],
                numeric_scale=row[7],
                is_identity=bool(row[8]),
            )
            for row in rows
        ]

    def get_primary_key(self, schema: str, table: str) -> list[str]:
        query = """
            SELECT kcu.COLUMN_NAME
            FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
            JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
              ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
             AND tc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA
            WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
              AND tc.TABLE_SCHEMA = ?
              AND tc.TABLE_NAME = ?
            ORDER BY kcu.ORDINAL_POSITION
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, [schema, table])
            return [row[0] for row in cursor.fetchall()]

    def get_foreign_keys(self, schema: str, table: str) -> list[ForeignKeyInfo]:
        query = """
            SELECT
                fk.name AS fk_name,
                ps.name AS source_schema,
                pt.name AS source_table,
                pc.name AS source_column,
                rs.name AS target_schema,
                rt.name AS target_table,
                rc.name AS target_column,
                fkc.constraint_column_id
            FROM sys.foreign_keys fk
            JOIN sys.foreign_key_columns fkc
              ON fk.object_id = fkc.constraint_object_id
            JOIN sys.tables pt
              ON fkc.parent_object_id = pt.object_id
            JOIN sys.schemas ps
              ON pt.schema_id = ps.schema_id
            JOIN sys.columns pc
              ON pc.object_id = pt.object_id
             AND pc.column_id = fkc.parent_column_id
            JOIN sys.tables rt
              ON fkc.referenced_object_id = rt.object_id
            JOIN sys.schemas rs
              ON rt.schema_id = rs.schema_id
            JOIN sys.columns rc
              ON rc.object_id = rt.object_id
             AND rc.column_id = fkc.referenced_column_id
            WHERE ps.name = ? AND pt.name = ?
            ORDER BY fk.name, fkc.constraint_column_id
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, [schema, table])
            rows = cursor.fetchall()

        grouped = {}
        for row in rows:
            item = grouped.setdefault(
                row[0],
                {
                    "source_schema": row[1],
                    "source_table": row[2],
                    "source_columns": [],
                    "target_schema": row[4],
                    "target_table": row[5],
                    "target_columns": [],
                },
            )
            item["source_columns"].append(row[3])
            item["target_columns"].append(row[6])

        return [
            ForeignKeyInfo(
                name=name,
                source_schema=data["source_schema"],
                source_table=data["source_table"],
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
            ", ".join(self.quote_identifier(column) for column in columns)
            if columns
            else "*"
        )
        params = []
        query = f"SELECT {selected} FROM {self.quote_identifier(schema)}.{self.quote_identifier(table)} "
        if cursor_field and cursor_gt is not None:
            query += f"WHERE {self.quote_identifier(cursor_field)} > ? "
            params.append(cursor_gt)
            query += f"ORDER BY {self.quote_identifier(cursor_field)} "
        else:
            query += "ORDER BY (SELECT NULL) "
        query += "OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
        params.extend([offset, limit])

        try:
            with self.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()
                columns_out = [column[0] for column in cursor.description]
                return {
                    "rows": [dict(zip(columns_out, row)) for row in rows],
                    "limit": limit,
                    "offset": offset,
                    "returned": len(rows),
                }
        except Exception as exc:
            raise ConnectorQueryError(str(exc)) from exc
    def execute_select(self, query, params=None):
        try:
            with self.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params or [])
                rows = cursor.fetchall()
                columns_out = [column[0] for column in cursor.description]
                payload = [dict(zip(columns_out, row)) for row in rows]
                return {"rows": payload, "returned": len(payload)}
        except Exception as exc:
            raise ConnectorQueryError(str(exc)) from exc

