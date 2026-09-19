"""Shared Query/Execution IR used by Operations and UER-facing dataset adapters.

OQP8 deliberately keeps this IR serializable.  It is a contract between planners
and executors, not SQL, so future Script/ML/Optimization nodes can share the same
execution layer without coupling Operations to one database engine.
"""
from __future__ import annotations

IR_VERSION = 1


def scan_node(*, table_id, source_id, fields):
    return {"op": "SCAN", "table_id": str(table_id), "source_id": str(source_id), "fields": list(fields)}


def join_node(*, left_table_id, right_table_id, pairs, relationship_id=None):
    return {
        "op": "JOIN", "join_type": "INNER",
        "left_table_id": str(left_table_id), "right_table_id": str(right_table_id),
        "pairs": [list(p) for p in pairs], "relationship_id": str(relationship_id or ""),
    }


def build_execution_ir(plan):
    table_source = {str(t["id"]): str(t.get("data_source_id") or "") for t in plan.get("tables", [])}
    fields_by_table = {}
    for f in plan.get("fields", []):
        fields_by_table.setdefault(str(f["table_id"]), []).append(f["field"])
    nodes = [scan_node(table_id=tid, source_id=source, fields=fields_by_table.get(tid, [])) for tid, source in table_source.items()]
    nodes += [join_node(left_table_id=j["from_table_id"], right_table_id=j["to_table_id"], pairs=j["pairs"], relationship_id=j.get("relationship_id")) for j in plan.get("joins", [])]
    return {"version": IR_VERSION, "kind": "QUERY", "nodes": nodes}


def dataset_node(*, asset_id, producer="DATA_ASSET", metadata=None):
    """UER-neutral reference for datasets produced by scripts/ML/optimization."""
    return {"op": "DATASET", "asset_id": str(asset_id), "producer": producer, "metadata": metadata or {}}
