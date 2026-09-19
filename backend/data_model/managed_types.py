LOGICAL_TYPE_SQL = {
    "INTEGER": "integer",
    "BIGINT": "bigint",
    "DECIMAL": "numeric",
    "FLOAT": "double precision",
    "BOOLEAN": "boolean",
    "STRING": "varchar",
    "TEXT": "text",
    "DATE": "date",
    "DATETIME": "timestamp without time zone",
    "DATETIME_TZ": "timestamp with time zone",
    "TIME": "time",
    "UUID": "uuid",
    "JSON": "jsonb",
    "BINARY": "bytea",
}


def supported_logical_types():
    return sorted(LOGICAL_TYPE_SQL)
