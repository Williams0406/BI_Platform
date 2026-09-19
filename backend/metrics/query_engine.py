import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from django.core.cache import cache
from django.db import connection

from .models import MetricDefinition, SemanticDimension


SQL_EXPR_FORBIDDEN = re.compile(
    r"\b(SELECT|FROM|JOIN|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)


class MetricQueryError(ValueError):
    pass



DAX_TABLE_FIELD = re.compile(r"(?:'[^']+'|[A-Za-z_][A-Za-z0-9_]*)\s*\[\s*([A-Za-z_][A-Za-z0-9_]*)\s*\]")


def _dax_to_sql(metric, expression):
    """Translate a deliberately small, aggregation-focused DAX subset to SQL.

    Supported: SUM, AVERAGE, MIN, MAX, COUNT, DISTINCTCOUNT, COUNTROWS,
    DIVIDE and arithmetic. Measure references / CALCULATE / filter context are
    intentionally outside this first implementation.
    """
    if not expression or not expression.strip():
        raise MetricQueryError("La expresión DAX está vacía.")
    if ";" in expression:
        raise MetricQueryError("No se permiten múltiples expresiones DAX.")

    allowed = _allowed_fields(metric)

    def field_ref(match):
        name = match.group(1)
        if name not in allowed:
            raise MetricQueryError(f"Campo DAX desconocido: {name}")
        return f"FIELD({name})"

    text = DAX_TABLE_FIELD.sub(field_ref, expression.strip())
    text = re.sub(r"COUNTROWS\s*\([^()]*\)", "COUNTROWS()", text, flags=re.I)

    token_re = re.compile(r"\s*(?:(\d+(?:\.\d+)?)|([A-Za-z_][A-Za-z0-9_]*)|([()+\-*/,:]))")
    tokens = []
    pos = 0
    while pos < len(text):
        match = token_re.match(text, pos)
        if not match:
            raise MetricQueryError(f"Sintaxis DAX no soportada cerca de: {text[pos:pos+25]}")
        tokens.append(match.group(1) or match.group(2) or match.group(3))
        pos = match.end()
    index = 0

    def peek():
        return tokens[index] if index < len(tokens) else None

    def take(value=None):
        nonlocal index
        token = peek()
        if token is None or (value is not None and token != value):
            raise MetricQueryError(f"DAX inválido; se esperaba {value or 'token'}.")
        index += 1
        return token

    def parse_primary():
        token = peek()
        if token == "(":
            take("(")
            value = parse_expr()
            take(")")
            return f"({value})"
        if token == "-":
            take("-")
            return f"(-{parse_primary()})"
        if token and re.fullmatch(r"\d+(?:\.\d+)?", token):
            return take()
        if token and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", token):
            name = take()
            if peek() == "(":
                take("(")
                args = []
                if peek() != ")":
                    while True:
                        # FIELD takes its bare field identifier without interpreting it as a function.
                        if name.upper() == "FIELD":
                            field = take()
                            if field not in allowed:
                                raise MetricQueryError(f"Campo DAX desconocido: {field}")
                            args.append(quote(field))
                        else:
                            args.append(parse_expr())
                        if peek() != ",":
                            break
                        take(",")
                take(")")
                fn = name.upper()
                if fn == "FIELD":
                    if len(args) != 1:
                        raise MetricQueryError("FIELD inválido.")
                    return args[0]
                if fn in {"SUM", "MIN", "MAX", "COUNT"} and len(args) == 1:
                    return f"{fn}({args[0]})"
                if fn == "AVERAGE" and len(args) == 1:
                    return f"AVG({args[0]})"
                if fn == "DISTINCTCOUNT" and len(args) == 1:
                    return f"COUNT(DISTINCT {args[0]})"
                if fn == "COUNTROWS" and not args:
                    return "COUNT(*)"
                if fn == "DIVIDE" and len(args) in {2, 3}:
                    alt = args[2] if len(args) == 3 else "NULL"
                    return f"CASE WHEN ({args[1]}) = 0 THEN {alt} ELSE ({args[0]})::numeric / ({args[1]}) END"
                raise MetricQueryError(f"Función DAX no soportada: {name}")
            raise MetricQueryError(f"Identificador DAX no soportado: {name}")
        raise MetricQueryError("Expresión DAX inválida.")

    def parse_mul():
        value = parse_primary()
        while peek() in {"*", "/"}:
            op = take()
            value = f"({value} {op} {parse_primary()})"
        return value

    def parse_expr():
        value = parse_mul()
        while peek() in {"+", "-"}:
            op = take()
            value = f"({value} {op} {parse_mul()})"
        return value

    result = parse_expr()
    if index != len(tokens):
        raise MetricQueryError("La expresión DAX contiene tokens no procesados.")
    return result


def _python_metric_result(metric, dimensions, filters, limit):
    fields = _allowed_fields(metric)
    selected_names = list(fields.keys())
    table = metric.semantic_model.base_table
    select_sql = ", ".join(quote(name) for name in selected_names)
    query = f"SELECT {select_sql} FROM {quote(table.schema_name)}.{quote(table.table_name)}"
    where_clauses, params = _build_filters(metric, filters)
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    # Python measures intentionally have a guardrail because they materialize rows.
    max_rows = 500000
    query += " LIMIT %s"
    params.append(max_rows + 1)
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        names = [col[0] for col in cursor.description]
        raw_rows = cursor.fetchall()
    if len(raw_rows) > max_rows:
        raise MetricQueryError(
            f"La medida Python excede el límite de {max_rows:,} filas. Filtre los datos o use SQL/DAX."
        )

    import pandas as pd
    frame = pd.DataFrame(raw_rows, columns=names)
    dimension_names = [dimension.field.name for dimension in dimensions]

    with tempfile.TemporaryDirectory(prefix="bi_metric_python_") as temp:
        root = Path(temp)
        frame.to_csv(root / "input.csv", index=False)
        (root / "measure.py").write_text(metric.expression, encoding="utf-8")
        manifest = {"dimensions": dimension_names}
        manifest_path = root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        runner = Path(__file__).with_name("python_metric_runner.py")
        try:
            completed = subprocess.run(
                [sys.executable, "-I", str(runner), str(manifest_path)],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise MetricQueryError("La medida Python excedió 60 segundos.") from exc
        if completed.returncode != 0:
            raise MetricQueryError(completed.stderr.strip() or "Falló la medida Python.")
        output = pd.read_csv(root / "output.csv")

    rename = {dimension.field.name: str(dimension.id) for dimension in dimensions}
    output = output.rename(columns=rename)
    rows = output.head(min(max(int(limit), 1), 5000)).where(output.notna(), None).to_dict(orient="records")
    return rows

def quote(identifier):
    return connection.ops.quote_name(identifier)


def _allowed_fields(metric):
    return {
        field.name: field
        for field in metric.semantic_model.base_table.fields.all()
    }


def _validate_sql_expression(metric, expression):
    if not expression.strip():
        raise MetricQueryError("La expresión SQL está vacía.")

    if ";" in expression:
        raise MetricQueryError("No se permiten múltiples sentencias.")

    if SQL_EXPR_FORBIDDEN.search(expression):
        raise MetricQueryError(
            "La expresión SQL de una métrica no puede contener sentencias completas."
        )

    fields = _allowed_fields(metric)
    for token in re.findall(r"\{\{field:([A-Za-z_][A-Za-z0-9_]*)\}\}", expression):
        if token not in fields:
            raise MetricQueryError(f"Campo no permitido en expresión: {token}")

    return expression


def render_metric_expression(metric):
    table = metric.semantic_model.base_table

    if metric.expression_type == MetricDefinition.ExpressionType.SIMPLE:
        if metric.aggregation == MetricDefinition.Aggregation.COUNT:
            return "COUNT(*)"

        if not metric.source_field:
            raise MetricQueryError(
                "La métrica SIMPLE requiere source_field excepto COUNT."
            )

        if metric.source_field.table_asset_id != table.id:
            raise MetricQueryError(
                "source_field no pertenece a la tabla base del SemanticModel."
            )

        field_sql = quote(metric.source_field.name)

        mapping = {
            MetricDefinition.Aggregation.SUM: f"SUM({field_sql})",
            MetricDefinition.Aggregation.AVG: f"AVG({field_sql})",
            MetricDefinition.Aggregation.MIN: f"MIN({field_sql})",
            MetricDefinition.Aggregation.MAX: f"MAX({field_sql})",
            MetricDefinition.Aggregation.COUNT_DISTINCT: f"COUNT(DISTINCT {field_sql})",
            MetricDefinition.Aggregation.NONE: field_sql,
        }
        if metric.aggregation not in mapping:
            raise MetricQueryError(
                f"Agregación no válida para SIMPLE: {metric.aggregation}"
            )
        return mapping[metric.aggregation]

    if metric.expression_type == MetricDefinition.ExpressionType.DAX:
        return _dax_to_sql(metric, metric.expression)

    if metric.expression_type == MetricDefinition.ExpressionType.PYTHON:
        raise MetricQueryError("Las medidas Python se ejecutan mediante el runtime Python, no como SQL.")

    expression = _validate_sql_expression(metric, metric.expression)
    fields = _allowed_fields(metric)

    def replace(match):
        name = match.group(1)
        if name not in fields:
            raise MetricQueryError(f"Campo desconocido: {name}")
        return quote(name)

    return re.sub(
        r"\{\{field:([A-Za-z_][A-Za-z0-9_]*)\}\}",
        replace,
        expression,
    )


def validate_dimensions(metric, dimension_ids):
    if not dimension_ids:
        return []

    dimensions = list(
        SemanticDimension.objects.filter(
            id__in=dimension_ids,
            semantic_model=metric.semantic_model,
        ).select_related("field")
    )

    found = {str(item.id) for item in dimensions}
    missing = [value for value in dimension_ids if str(value) not in found]
    if missing:
        raise MetricQueryError(
            "Dimensiones inválidas para la métrica: " + ", ".join(map(str, missing))
        )

    return dimensions


def _build_filters(metric, filters):
    if not filters:
        return [], []

    fields = _allowed_fields(metric)
    clauses = []
    params = []

    operators = {
        "eq": "=",
        "ne": "<>",
        "gt": ">",
        "gte": ">=",
        "lt": "<",
        "lte": "<=",
        "contains": "ILIKE",
        "in": "IN",
    }

    for item in filters:
        field_name = item.get("field")
        operator = item.get("operator", "eq")
        value = item.get("value")

        if field_name not in fields:
            raise MetricQueryError(f"Filtro usa campo desconocido: {field_name}")
        if operator not in operators:
            raise MetricQueryError(f"Operador de filtro inválido: {operator}")

        if operator == "contains":
            clauses.append(f"{quote(field_name)} ILIKE %s")
            params.append(f"%{value}%")
        elif operator == "in":
            if not isinstance(value, list) or not value:
                raise MetricQueryError("El operador IN requiere una lista no vacía.")
            placeholders = ", ".join(["%s"] * len(value))
            clauses.append(f"{quote(field_name)} IN ({placeholders})")
            params.extend(value)
        else:
            clauses.append(f"{quote(field_name)} {operators[operator]} %s")
            params.append(value)

    return clauses, params


def _cache_key(metric, dimension_ids, filters, limit):
    payload = repr((str(metric.id), tuple(map(str, dimension_ids or [])), filters or [], limit))
    return f"metric-query:{hash(payload)}"


def execute_metric(metric, dimension_ids=None, filters=None, limit=1000, use_cache=True):
    if not metric.enabled:
        raise MetricQueryError("La métrica está deshabilitada.")

    key = _cache_key(metric, dimension_ids, filters, limit)
    if use_cache:
        cached = cache.get(key)
        if cached is not None:
            return {**cached, "cached": True}

    dimensions = validate_dimensions(metric, dimension_ids or [])

    if metric.expression_type == MetricDefinition.ExpressionType.PYTHON:
        rows = _python_metric_result(metric, dimensions, filters or [], limit)
        result = {
            "metric": {
                "id": str(metric.id),
                "name": metric.name,
                "format_type": metric.format_type,
                "unit": metric.unit,
                "decimal_places": metric.decimal_places,
            },
            "dimensions": [
                {
                    "id": str(d.id),
                    "name": d.name,
                    "field": d.field.name,
                    "dimension_type": d.dimension_type,
                }
                for d in dimensions
            ],
            "rows": rows,
            "returned": len(rows),
            "cached": False,
        }
        if use_cache:
            cache.set(key, result, timeout=metric.cache_ttl_seconds)
        return result

    expression = render_metric_expression(metric)

    select_parts = []
    group_parts = []

    for dimension in dimensions:
        field_sql = quote(dimension.field.name)
        select_parts.append(
            f"{field_sql} AS {quote(str(dimension.id))}"
        )
        group_parts.append(field_sql)

    select_parts.append(f"{expression} AS {quote('value')}")

    table = metric.semantic_model.base_table
    query = (
        f"SELECT {', '.join(select_parts)} "
        f"FROM {quote(table.schema_name)}.{quote(table.table_name)}"
    )

    where_clauses, params = _build_filters(metric, filters)
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    if group_parts:
        query += " GROUP BY " + ", ".join(group_parts)
        query += " ORDER BY " + ", ".join(group_parts)

    query += " LIMIT %s"
    params.append(min(max(int(limit), 1), 5000))

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        names = [col[0] for col in cursor.description]
        rows = [dict(zip(names, row)) for row in cursor.fetchall()]

    result = {
        "metric": {
            "id": str(metric.id),
            "name": metric.name,
            "format_type": metric.format_type,
            "unit": metric.unit,
            "decimal_places": metric.decimal_places,
        },
        "dimensions": [
            {
                "id": str(d.id),
                "name": d.name,
                "field": d.field.name,
                "dimension_type": d.dimension_type,
            }
            for d in dimensions
        ],
        "rows": rows,
        "returned": len(rows),
        "cached": False,
    }

    if use_cache:
        cache.set(key, result, timeout=metric.cache_ttl_seconds)

    return result
