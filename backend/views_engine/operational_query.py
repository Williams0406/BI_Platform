"""Operational Query Planner for Operational Views.

The planner converts builder IR bindings into logical component datasets and
executes safe, server-side projections/filters/pagination against MANAGED
Platform tables.  Multi-table components are resolved through active Data Model
relationships; no relationship is invented implicitly.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

from django.db import connection
from django.conf import settings

from connectors.query_plan import compile_select_plan, capabilities_for_engine
from connectors.registry import build_connector
from execution.query_ir import build_execution_ir
from .cross_source import CrossSourceError, materialize_fragment, join_rows, limits as cross_source_limits

from data_model.models import FieldAsset, RelationAsset, TableAsset
from datasources.models import DataSource
from data_records.services import quote, serialize_row


class OperationalQueryError(ValueError):
    pass


@dataclass(frozen=True)
class FieldRef:
    table_id: str
    field_id: str


def _refs(component: dict[str, Any]) -> list[FieldRef]:
    out: list[FieldRef] = []
    for value in (component.get("slots") or {}).values():
        values = value if isinstance(value, list) else ([value] if value else [])
        for ref in values:
            if isinstance(ref, dict) and ref.get("tableId") and ref.get("fieldId"):
                out.append(FieldRef(str(ref["tableId"]), str(ref["fieldId"])))
    # stable de-duplication
    return list(dict.fromkeys(out))


def _workspace_tables(view, ids: set[str]) -> dict[str, TableAsset]:
    qs = (
        TableAsset.objects.filter(id__in=ids, data_source__workspace_id=view.workspace_id)
        .select_related("data_source")
        .prefetch_related("fields")
    )
    tables = {str(t.id): t for t in qs}
    missing = ids - set(tables)
    if missing:
        raise OperationalQueryError("One or more Operational View tables are not available in this workspace.")
    return tables


def _field_maps(tables: dict[str, TableAsset]):
    by_id = {}
    by_table_name = defaultdict(dict)
    for table_id, table in tables.items():
        for field in table.fields.all():
            by_id[str(field.id)] = field
            by_table_name[table_id][field.name] = field
    return by_id, by_table_name


def _relations(view, table_ids: set[str]):
    return list(
        RelationAsset.objects.filter(
            is_active=True,
            source_table__data_source__workspace_id=view.workspace_id,
            source_table_id__in=table_ids,
        )
        .filter(target_table__data_source__workspace_id=view.workspace_id)
        .select_related("source_table", "target_table")
    )


def _graph(view):
    relations = list(
        RelationAsset.objects.filter(
            is_active=True,
            source_table__data_source__workspace_id=view.workspace_id,
            target_table__data_source__workspace_id=view.workspace_id,
        ).select_related("source_table", "target_table")
    )
    graph = defaultdict(list)
    for rel in relations:
        a, b = str(rel.source_table_id), str(rel.target_table_id)
        graph[a].append((b, rel, True))
        graph[b].append((a, rel, False))
    return graph


def _shortest_path(graph, start: str, target: str):
    if start == target:
        return []
    queue = deque([(start, [])])
    seen = {start}
    while queue:
        node, path = queue.popleft()
        for nxt, rel, forward in graph.get(node, []):
            if nxt in seen:
                continue
            new_path = path + [(node, nxt, rel, forward)]
            if nxt == target:
                return new_path
            seen.add(nxt)
            queue.append((nxt, new_path))
    return None


def _relation_pairs(rel: RelationAsset, forward: bool):
    left = list(rel.source_columns or [])
    right = list(rel.target_columns or [])
    if not left or len(left) != len(right):
        raise OperationalQueryError(f"Relationship {rel.name} has an invalid column mapping.")
    return list(zip(left, right)) if forward else list(zip(right, left))


def _table_label(table: TableAsset) -> str:
    return table.technical_name or table.table_name


def _execution_profile(tables: dict[str, TableAsset]) -> dict[str, Any]:
    sources = {str(t.data_source_id): t.data_source for t in tables.values()}
    if len(sources) != 1:
        profiles = []
        for source in sources.values():
            if source.status != DataSource.Status.ACTIVE or not source.can_read:
                raise OperationalQueryError(f"Data source '{source.name}' is not readable/ACTIVE.")
            caps = capabilities_for_engine(source.engine)
            if not caps.get("pagination"):
                raise OperationalQueryError(f"OQP7 cross-source pushdown is not supported for engine={source.engine}.")
            profiles.append({"data_source_id": str(source.id), "data_source": source.name, "mode": source.mode, "engine": source.engine, "capabilities": caps})
        return {
            "strategy": "CROSS_SOURCE_MATERIALIZE", "mode": "CROSS_SOURCE", "engine": "MULTI",
            "sources": profiles, "capabilities": {"cross_source": True, "materialization": "BOUNDED_EPHEMERAL", "cache": True},
        }
    source = next(iter(sources.values()))
    if source.status != DataSource.Status.ACTIVE:
        raise OperationalQueryError(f"Data source '{source.name}' is not ACTIVE.")
    if not source.can_read:
        raise OperationalQueryError(f"Data source '{source.name}' does not have READ capability enabled.")
    caps = capabilities_for_engine(source.engine)
    if not caps.get("pagination"):
        raise OperationalQueryError(f"OQP6 pushdown is not supported for engine={source.engine}.")
    strategy = {
        DataSource.Mode.MANAGED: "PLATFORM_SQL_PUSHDOWN",
        DataSource.Mode.EXTERNAL: "EXTERNAL_SQL_PUSHDOWN",
        DataSource.Mode.PRIVATE_GATEWAY: "PRIVATE_GATEWAY_PUSHDOWN",
    }.get(source.mode)
    if not strategy:
        raise OperationalQueryError(f"Unsupported data source mode: {source.mode}.")
    if source.mode == DataSource.Mode.PRIVATE_GATEWAY:
        try:
            binding = source.gateway_binding
            gateway = binding.gateway
        except Exception as exc:
            raise OperationalQueryError("Private source has no Gateway binding.") from exc
        if not binding.enabled:
            raise OperationalQueryError("Private source Gateway binding is disabled.")
        operations = (gateway.capabilities or {}).get("operations") or []
        if "QUERY_PLAN" not in operations:
            raise OperationalQueryError(
                "The connected Private Gateway does not advertise OQP6 QUERY_PLAN capability. Update/restart the agent."
            )
    return {
        "data_source_id": str(source.id),
        "data_source": source.name,
        "mode": source.mode,
        "engine": source.engine,
        "strategy": strategy,
        "capabilities": caps,
    }


def build_component_plan(view, component: dict[str, Any], graph=None) -> dict[str, Any] | None:
    refs = _refs(component)
    if not refs:
        return None
    requested_ids = {r.table_id for r in refs}
    # Relationship paths may introduce bridge tables; load them after path discovery.
    graph = graph or _graph(view)
    root_id = refs[0].table_id
    paths = []
    all_table_ids = set(requested_ids)
    for table_id in requested_ids:
        path = _shortest_path(graph, root_id, table_id)
        if path is None:
            raise OperationalQueryError(
                "No active Data Model relationship connects all fields used by "
                f"component '{component.get('title') or component.get('type')}'."
            )
        paths.extend(path)
        for a, b, _, _ in path:
            all_table_ids.update([a, b])

    tables = _workspace_tables(view, all_table_ids)
    field_by_id, _ = _field_maps(tables)
    fields = []
    for ref in refs:
        field = field_by_id.get(ref.field_id)
        if not field or str(field.table_asset_id) != ref.table_id:
            raise OperationalQueryError("An Operational View field binding is stale or invalid.")
        fields.append((ref, field))

    # Unique relationship edges in traversal order.
    joins = []
    seen_edges = set()
    for a, b, rel, forward in paths:
        key = (str(rel.id), forward)
        if key in seen_edges:
            continue
        seen_edges.add(key)
        joins.append({
            "from_table_id": a,
            "to_table_id": b,
            "relationship_id": str(rel.id),
            "relationship": rel.name,
            "pairs": _relation_pairs(rel, forward),
        })

    return {
        "component_id": str(component.get("id") or ""),
        "component_type": component.get("type") or "",
        "root_table_id": root_id,
        "tables": [
            {"id": tid, "technical_name": _table_label(tables[tid]), "data_source_id": str(tables[tid].data_source_id)}
            for tid in all_table_ids
        ],
        "fields": [
            {
                "table_id": ref.table_id,
                "field_id": ref.field_id,
                "table": _table_label(tables[ref.table_id]),
                "field": field.name,
                "logical_type": field.logical_type,
            }
            for ref, field in fields
        ],
        "joins": joins,
        "execution": _execution_profile(tables),
        "execution_ir": None,
        "lineage": [
            {"output": f"{_table_label(tables[ref.table_id])}__{field.name}", "table_id": ref.table_id, "field_id": ref.field_id, "table": _table_label(tables[ref.table_id]), "field": field.name}
            for ref, field in fields
        ],
    }


def build_operational_plan(view) -> dict[str, Any]:
    ir = (view.config or {}).get("builder_ir") or {}
    graph = _graph(view)
    components = []
    errors = []
    for component in ir.get("components") or []:
        try:
            plan = build_component_plan(view, component, graph=graph)
            if plan:
                plan["execution_ir"] = build_execution_ir(plan)
                components.append(plan)
        except OperationalQueryError as exc:
            errors.append({"component_id": str(component.get("id") or ""), "detail": str(exc)})
    return {
        "version": 1,
        "view_id": str(view.id),
        "workspace_id": str(view.workspace_id),
        "components": components,
        "errors": errors,
    }


def _physical_plan(view, plan, *, limit=50, offset=0, filters=None, order_by=None, selected_rows=None):
    plan = _augment_plan_for_context(view, plan, selected_rows or {})
    table_ids = {x["id"] for x in plan["tables"]}
    tables = _workspace_tables(view, table_ids)
    execution = _execution_profile(tables)
    if execution.get("strategy") == "CROSS_SOURCE_MATERIALIZE":
        raise OperationalQueryError("Cross-source plans are executed by the OQP7 materialization executor.")
    if execution["data_source_id"] != plan.get("execution", {}).get("data_source_id"):
        raise OperationalQueryError("Master-detail context changed execution source unexpectedly.")

    identity_meta = _primary_key_fields(tables)
    select = []
    for item in plan["fields"]:
        select.append({
            "table_id": item["table_id"], "field": item["field"],
            "output": f"{item['table']}__{item['field']}", "kind": "field",
        })
    # Row identity is preserved for every source. Row version is Platform-only.
    for tid, meta in identity_meta.items():
        for pk in meta["primary_key"]:
            select.append({"table_id": tid, "field": pk, "output": f"__oqp_pk__{tid}__{pk}", "kind": "identity"})
        if execution["mode"] == DataSource.Mode.MANAGED and meta.get("row_version_column"):
            select.append({"table_id": tid, "field": meta["row_version_column"], "output": f"__oqp_ver__{tid}", "kind": "version"})

    allowed_fields = {(x["table_id"], x["field"]) for x in plan["fields"]}
    safe_filters = []
    for item in filters or []:
        tid = str(item.get("table_id") or plan["root_table_id"])
        name = item.get("field")
        if (tid, name) not in allowed_fields:
            continue
        op = item.get("operator") or "contains"
        if op not in execution["capabilities"].get("filter", []):
            raise OperationalQueryError(f"Filter operator '{op}' is not supported by this source.")
        safe_filters.append({"table_id": tid, "field": name, "operator": op, "value": item.get("value")})

    for tid, selected in (selected_rows or {}).items():
        tid = str(tid)
        if tid not in tables:
            continue
        identity = (selected or {}).get("identity") or {}
        for pk in (identity_meta.get(tid) or {}).get("primary_key") or []:
            if pk in identity:
                safe_filters.append({"table_id": tid, "field": pk, "operator": "eq", "value": identity[pk]})

    safe_order = None
    if order_by:
        tid = str(order_by.get("table_id") or plan["root_table_id"])
        name = order_by.get("field")
        if (tid, name) in allowed_fields:
            safe_order = {"table_id": tid, "field": name, "descending": bool(order_by.get("descending"))}

    ordered_ids = [plan["root_table_id"]] + sorted(table_ids - {plan["root_table_id"]})
    return {
        "version": 1,
        "root_table_id": plan["root_table_id"],
        "tables": [
            {"id": tid, "schema": tables[tid].schema_name, "table": tables[tid].table_name}
            for tid in ordered_ids
        ],
        "select": select,
        "joins": plan["joins"],
        "filters": safe_filters,
        "order_by": safe_order,
        "limit": min(max(int(limit), 1), int(execution["capabilities"].get("max_page_size") or 500)),
        "offset": max(int(offset), 0),
        "execution": execution,
    }, plan, tables, identity_meta


def _wait_gateway_query(job):
    import time
    from customer_gateway.models import GatewayJob
    timeout = int(getattr(settings, "OQP_GATEWAY_QUERY_TIMEOUT_SECONDS", 30))
    deadline = time.monotonic() + max(1, timeout)
    while time.monotonic() < deadline:
        job.refresh_from_db()
        if job.status == GatewayJob.Status.SUCCESS:
            return job.result or {}
        if job.status in {GatewayJob.Status.FAILED, GatewayJob.Status.CANCELLED, GatewayJob.Status.EXPIRED}:
            raise OperationalQueryError(job.error_message or f"Gateway query {job.status}.")
        time.sleep(0.25)
    raise OperationalQueryError("Private Gateway did not complete the OQP6 query before timeout.")


def _execute_physical_plan(physical, user=None):
    execution = physical["execution"]
    engine = execution["engine"]
    mode = execution["mode"]
    source = DataSource.objects.get(id=execution["data_source_id"])
    if mode == DataSource.Mode.PRIVATE_GATEWAY:
        from customer_gateway.models import GatewayJob
        from customer_gateway.services import queue_job
        job = queue_job(source, GatewayJob.Operation.QUERY_PLAN, {"plan": {k: v for k, v in physical.items() if k != "execution"}}, user=user)
        return _wait_gateway_query(job)

    query, params = compile_select_plan(physical, engine)
    if mode == DataSource.Mode.MANAGED:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            names = [c[0] for c in cursor.description]
            rows = [dict(zip(names, row)) for row in cursor.fetchall()]
            return {"rows": rows, "returned": len(rows)}
    if mode == DataSource.Mode.EXTERNAL:
        connector = build_connector(source)
        return connector.execute_select(query, params)
    raise OperationalQueryError(f"Unsupported OQP6 execution mode: {mode}")



def _execute_cross_source_component(view, plan, *, limit=50, offset=0, filters=None, order_by=None, selected_rows=None, user=None):
    """Execute OQP7 by bounded per-table pushdown + ephemeral materialization/cache."""
    table_ids = {x["id"] for x in plan["tables"]}
    tables = _workspace_tables(view, table_ids)
    identity_meta = _primary_key_fields(tables)
    relation_fields = defaultdict(set)
    for join in plan.get("joins") or []:
        for left, right in join["pairs"]:
            relation_fields[str(join["from_table_id"])].add(left)
            relation_fields[str(join["to_table_id"])].add(right)
    requested = defaultdict(set)
    for f in plan["fields"]:
        requested[str(f["table_id"])].add(f["field"])
    for tid, meta in identity_meta.items():
        requested[tid].update(meta["primary_key"])
    for tid, names in relation_fields.items():
        requested[tid].update(names)

    filters = filters or []
    fragments, cache_hits = {}, 0
    max_rows = cross_source_limits()["max_rows_per_fragment"]
    for tid, table in tables.items():
        source = table.data_source
        caps = capabilities_for_engine(source.engine)
        local_filters = []
        for item in filters:
            item_tid = str(item.get("table_id") or plan["root_table_id"])
            if item_tid != tid or item.get("field") not in requested[tid]:
                continue
            op = item.get("operator") or "contains"
            if op not in caps.get("filter", []):
                raise OperationalQueryError(f"Filter operator '{op}' is not supported by source '{source.name}'.")
            local_filters.append({"table_id": tid, "field": item["field"], "operator": op, "value": item.get("value")})
        selected = (selected_rows or {}).get(tid) or (selected_rows or {}).get(str(tid)) or {}
        for pk, value in (selected.get("identity") or {}).items():
            if pk in requested[tid]:
                local_filters.append({"table_id": tid, "field": pk, "operator": "eq", "value": value})
        select = [{"table_id": tid, "field": name, "output": f"{tid}__{name}", "kind": "field"} for name in sorted(requested[tid])]
        fragment = {
            "version": 1, "root_table_id": tid,
            "tables": [{"id": tid, "schema": table.schema_name, "table": table.table_name}],
            "select": select, "joins": [], "filters": local_filters, "order_by": None,
            "limit": max_rows, "offset": 0,
            "execution": _execution_profile({tid: table}),
        }
        result, hit = materialize_fragment(fragment, lambda f: _execute_physical_plan(f, user=user))
        cache_hits += int(hit)
        fragments[tid] = [serialize_row(r) for r in (result.get("rows") or [])]

    root = str(plan["root_table_id"])
    rows = fragments.get(root, [])
    joined = {root}
    pending = list(plan.get("joins") or [])
    # Join edges whose one side is already in the accumulated materialization.
    while pending:
        progressed = False
        for join in list(pending):
            a, b = str(join["from_table_id"]), str(join["to_table_id"])
            if a in joined and b not in joined:
                rows = join_rows(rows, fragments[b], left_prefix=a, right_prefix=b, pairs=join["pairs"])
                joined.add(b); pending.remove(join); progressed = True
            elif b in joined and a not in joined:
                reversed_pairs = [(r, l) for l, r in join["pairs"]]
                rows = join_rows(rows, fragments[a], left_prefix=b, right_prefix=a, pairs=reversed_pairs)
                joined.add(a); pending.remove(join); progressed = True
            elif a in joined and b in joined:
                pending.remove(join); progressed = True
        if not progressed:
            raise OperationalQueryError("OQP7 could not connect all cross-source materializations.")

    if order_by:
        tid = str(order_by.get("table_id") or root); field = order_by.get("field")
        key = f"{tid}__{field}"
        rows.sort(key=lambda r: (r.get(key) is None, r.get(key)), reverse=bool(order_by.get("descending")))
    total = len(rows)
    page = rows[max(int(offset), 0): max(int(offset), 0) + max(int(limit), 1)]
    counts = defaultdict(int)
    for f in plan["fields"]: counts[f["field"]] += 1
    output = []
    for row in page:
        item, identities = {}, {}
        for f in plan["fields"]:
            value = row.get(f"{f['table_id']}__{f['field']}")
            item[f"{f['table']}__{f['field']}"] = value
            if counts[f["field"]] == 1: item[f["field"]] = value
        for tid, meta in identity_meta.items():
            ident = {pk: row.get(f"{tid}__{pk}") for pk in meta["primary_key"]}
            if any(v is not None for v in ident.values()): identities[tid] = ident
        item["__row_identity"] = identities
        item["__row_versions"] = {}
        output.append(item)
    return {
        "rows": output, "limit": max(int(limit), 1), "offset": max(int(offset), 0), "returned": len(output),
        "total_materialized": total, "lineage": plan.get("lineage", []),
        "execution": {**plan["execution"], "cache_hits": cache_hits, "materialization_limit": max_rows},
    }

def _execute_component(view, plan, *, limit=50, offset=0, filters=None, order_by=None, selected_rows=None, user=None):
    if plan.get("execution", {}).get("strategy") == "CROSS_SOURCE_MATERIALIZE":
        return _execute_cross_source_component(view, plan, limit=limit, offset=offset, filters=filters, order_by=order_by, selected_rows=selected_rows, user=user)
    physical, logical_plan, tables, identity_meta = _physical_plan(
        view, plan, limit=limit, offset=offset, filters=filters,
        order_by=order_by, selected_rows=selected_rows,
    )
    result = _execute_physical_plan(physical, user=user)
    raw = [serialize_row(row) for row in (result.get("rows") or [])]

    counts = defaultdict(int)
    for f in logical_plan["fields"]:
        counts[f["field"]] += 1
    rows = []
    for row in raw:
        expanded = {k: v for k, v in row.items() if not k.startswith("__oqp_")}
        identities, versions = {}, {}
        for tid, meta in identity_meta.items():
            ident = {pk: row.get(f"__oqp_pk__{tid}__{pk}") for pk in meta["primary_key"]}
            if ident and any(v is not None for v in ident.values()):
                identities[tid] = ident
            if physical["execution"]["mode"] == DataSource.Mode.MANAGED:
                versions[tid] = row.get(f"__oqp_ver__{tid}")
        expanded["__row_identity"] = identities
        expanded["__row_versions"] = versions
        for f in logical_plan["fields"]:
            if counts[f["field"]] == 1:
                expanded[f["field"]] = row.get(f"{f['table']}__{f['field']}")
        rows.append(expanded)
    return {
        "rows": rows, "limit": physical["limit"], "offset": physical["offset"],
        "returned": len(rows), "lineage": logical_plan.get("lineage", []),
        "execution": physical["execution"],
    }

def execute_operational_plan(view, payload=None, user=None):
    payload = payload or {}
    logical = build_operational_plan(view)
    errors = list(logical["errors"])
    datasets = {}
    # Deduplicate equivalent component plans during this request.
    cache = {}
    component_options = payload.get("components") or {}
    for plan in logical["components"]:
        cid = plan["component_id"]
        opts = component_options.get(cid) or {}
        signature = repr((plan["root_table_id"], plan["fields"], plan["joins"], opts))
        if signature not in cache:
            try:
                cache[signature] = _execute_component(
                    view, plan,
                    limit=opts.get("limit", payload.get("limit", 50)),
                    offset=opts.get("offset", 0),
                    filters=opts.get("filters", []),
                    order_by=opts.get("order_by"),
                    selected_rows=opts.get("selected_rows", payload.get("selected_rows", {})),
                    user=user,
                )
            except Exception as exc:
                errors.append({"component_id": cid, "detail": str(exc)})
                cache[signature] = {"rows": [], "limit": 0, "offset": 0, "returned": 0}
        datasets[cid] = cache[signature]
    return {"plan": logical, "datasets": datasets, "errors": errors}


def _primary_key_fields(tables):
    """Return catalog-backed row identity metadata for every table in a plan."""
    result = {}
    for tid, table in tables.items():
        pk_names = list(table.primary_key_columns or [])
        if not pk_names:
            pk_names = [f.name for f in table.fields.all() if f.is_primary_key]
        result[tid] = {
            "table_id": tid,
            "table": _table_label(table),
            "primary_key": pk_names,
            "row_version_column": table.row_version_column or "__row_version",
        }
    return result


def _augment_plan_for_context(view, plan, selected_rows):
    """Extend a component plan with relationship paths needed by master-detail context."""
    if not selected_rows:
        return plan
    graph = _graph(view)
    augmented = {**plan, "tables": list(plan["tables"]), "joins": list(plan["joins"])}
    table_ids = {x["id"] for x in augmented["tables"]}
    seen_rel = {(j["relationship_id"], j["from_table_id"], j["to_table_id"]) for j in augmented["joins"]}
    for selected_tid in selected_rows:
        selected_tid = str(selected_tid)
        if selected_tid in table_ids:
            continue
        path = _shortest_path(graph, plan["root_table_id"], selected_tid)
        if path is None:
            continue
        path_ids = {x for edge in path for x in edge[:2]}
        extra_tables = _workspace_tables(view, path_ids)
        for tid, table in extra_tables.items():
            if tid not in table_ids:
                augmented["tables"].append({"id": tid, "technical_name": _table_label(table)})
                table_ids.add(tid)
        for a, b, rel, forward in path:
            key = (str(rel.id), a, b)
            if key not in seen_rel:
                augmented["joins"].append({
                    "from_table_id": a,
                    "to_table_id": b,
                    "relationship_id": str(rel.id),
                    "relationship": rel.name,
                    "pairs": _relation_pairs(rel, forward),
                })
                seen_rel.add(key)
    return augmented


def execute_operational_writeback(view, payload, user=None):
    """Update exactly one lineage-qualified Platform row.

    The browser must send the table id, row identity and field/value.  We never
    infer a destination table from a joined display label.
    """
    from data_records.services import update_record
    from governance.models import WorkspacePolicy

    try:
        policy = view.workspace.governance_policy
    except WorkspacePolicy.DoesNotExist:
        policy = None
    if not policy or not policy.allow_operational_writeback:
        raise OperationalQueryError("Operational writeback is disabled by workspace Governance policy.")

    table_id = str(payload.get("table_id") or "")
    field_name = str(payload.get("field") or "")
    identity = payload.get("row_identity") or {}
    expected_version = payload.get("expected_version")
    if not table_id or not field_name:
        raise OperationalQueryError("table_id and field are required for governed writeback.")

    tables = _workspace_tables(view, {table_id})
    table = tables[table_id]
    if table.data_source.mode != DataSource.Mode.MANAGED:
        raise OperationalQueryError("OQP5 writeback remains Platform-only; OQP6 enables read pushdown for External/Private sources.")
    fields = {f.name: f for f in table.fields.all()}
    field = fields.get(field_name)
    if not field:
        raise OperationalQueryError("The requested writeback field does not belong to the target table.")
    if field.is_primary_key or field.is_identity:
        raise OperationalQueryError("Primary-key/identity fields cannot be edited from an Operational View.")

    pk_names = list(table.primary_key_columns or []) or [f.name for f in fields.values() if f.is_primary_key]
    if len(pk_names) != 1:
        raise OperationalQueryError("Operational writeback currently requires a single-column primary key.")
    pk = pk_names[0]
    record_key = identity.get(pk)
    if record_key is None:
        raise OperationalQueryError(f"Row identity is missing primary key '{pk}'.")
    if expected_version is None:
        raise OperationalQueryError("expected_version is required for optimistic concurrency.")

    row = update_record(table, record_key, {field_name: payload.get("value")}, expected_version=expected_version)
    return {
        "row": row,
        "lineage": {"table_id": table_id, "table": _table_label(table), "field": field_name, "primary_key": pk},
    }
