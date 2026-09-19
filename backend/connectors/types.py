from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class ColumnInfo:
    name: str
    data_type: str
    native_type: str
    nullable: bool
    ordinal_position: int
    default: Any = None
    max_length: int | None = None
    numeric_precision: int | None = None
    numeric_scale: int | None = None
    is_identity: bool = False

    def to_dict(self):
        return asdict(self)


@dataclass(slots=True)
class ForeignKeyInfo:
    name: str
    source_schema: str
    source_table: str
    source_columns: list[str]
    target_schema: str
    target_table: str
    target_columns: list[str]

    def to_dict(self):
        return asdict(self)


@dataclass(slots=True)
class TableInfo:
    schema: str
    name: str
    table_type: str = "TABLE"
    columns: list[ColumnInfo] = field(default_factory=list)
    primary_key: list[str] = field(default_factory=list)
    foreign_keys: list[ForeignKeyInfo] = field(default_factory=list)

    def to_dict(self):
        return {
            "schema": self.schema,
            "name": self.name,
            "table_type": self.table_type,
            "columns": [c.to_dict() for c in self.columns],
            "primary_key": list(self.primary_key),
            "foreign_keys": [fk.to_dict() for fk in self.foreign_keys],
        }
