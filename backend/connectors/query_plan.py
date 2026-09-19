"""Safe SQL compiler for OQP structured SELECT plans.

The compiler accepts catalog-backed identifiers only. Values always travel as
bound parameters; callers must validate table/field ids before building a plan.
"""
from __future__ import annotations


def capabilities_for_engine(engine: str) -> dict:
    common = {
        "project": True,
        "filter": ["eq", "contains"],
        "sort": True,
        "pagination": True,
        "join": True,
        "join_types": ["LEFT"],
        "aggregate": ["count", "sum", "avg", "min", "max"],
        "max_page_size": 500,
    }
    if engine in {"POSTGRESQL", "PLATFORM_POSTGRES"}:
        return {**common, "dialect": "postgresql", "case_insensitive_contains": True}
    if engine == "SQLSERVER":
        return {**common, "dialect": "sqlserver", "case_insensitive_contains": True}
    return {"project": True, "filter": [], "sort": False, "pagination": False, "join": False, "aggregate": [], "max_page_size": 100}


def _quote(engine: str, value: str) -> str:
    if engine == "SQLSERVER":
        return "[" + str(value).replace("]", "]]" ) + "]"
    return '"' + str(value).replace('"', '""') + '"'


def compile_select_plan(plan: dict, engine: str):
    """Compile a validated structured OQP physical plan to SQL + parameters."""
    if engine not in {"POSTGRESQL", "PLATFORM_POSTGRES", "SQLSERVER"}:
        raise ValueError(f"OQP pushdown is not supported for engine={engine}.")
    q = lambda x: _quote(engine, x)
    placeholder = "?" if engine == "SQLSERVER" else "%s"
    aliases = {str(t["id"]): f"t{i}" for i, t in enumerate(plan["tables"])}
    table_map = {str(t["id"]): t for t in plan["tables"]}
    root_id = str(plan["root_table_id"])

    select_parts = []
    for item in plan.get("select") or []:
        tid = str(item["table_id"])
        select_parts.append(f"{aliases[tid]}.{q(item['field'])} AS {q(item['output'])}")
    if not select_parts:
        raise ValueError("OQP physical plan has no projected fields.")

    root = table_map[root_id]
    sql = [f"SELECT {', '.join(select_parts)} FROM {q(root['schema'])}.{q(root['table'])} {aliases[root_id]}"]
    joined = {root_id}
    pending = list(plan.get("joins") or [])
    while pending:
        progressed = False
        for join in pending[:]:
            a, b = str(join["from_table_id"]), str(join["to_table_id"])
            if a not in joined:
                continue
            target = table_map[b]
            conditions = [f"{aliases[a]}.{q(left)} = {aliases[b]}.{q(right)}" for left, right in join["pairs"]]
            sql.append(f" LEFT JOIN {q(target['schema'])}.{q(target['table'])} {aliases[b]} ON " + " AND ".join(conditions))
            joined.add(b)
            pending.remove(join)
            progressed = True
        if not progressed:
            raise ValueError("OQP relationship plan could not be linearized safely.")

    params = []
    where = []
    for item in plan.get("filters") or []:
        tid, name, op = str(item["table_id"]), item["field"], item.get("operator") or "contains"
        value = item.get("value")
        if value in (None, ""):
            continue
        if op == "eq":
            where.append(f"{aliases[tid]}.{q(name)} = {placeholder}")
            params.append(value)
        elif op == "contains":
            if engine == "SQLSERVER":
                where.append(f"LOWER(CAST({aliases[tid]}.{q(name)} AS NVARCHAR(MAX))) LIKE LOWER({placeholder})")
            else:
                where.append(f"CAST({aliases[tid]}.{q(name)} AS TEXT) ILIKE {placeholder}")
            params.append(f"%{value}%")
        else:
            raise ValueError(f"Unsupported OQP filter operator: {op}")
    if where:
        sql.append(" WHERE " + " AND ".join(where))

    order = plan.get("order_by") or {}
    if order:
        tid = str(order["table_id"])
        sql.append(f" ORDER BY {aliases[tid]}.{q(order['field'])} {'DESC' if order.get('descending') else 'ASC'}")
    elif engine == "SQLSERVER":
        sql.append(" ORDER BY (SELECT NULL)")

    limit = min(max(int(plan.get("limit", 50)), 1), 500)
    offset = max(int(plan.get("offset", 0)), 0)
    if engine == "SQLSERVER":
        sql.append(f" OFFSET {placeholder} ROWS FETCH NEXT {placeholder} ROWS ONLY")
        params.extend([offset, limit])
    else:
        sql.append(f" LIMIT {placeholder} OFFSET {placeholder}")
        params.extend([limit, offset])
    return "".join(sql), params
