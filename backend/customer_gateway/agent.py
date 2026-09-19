"""
Customer Data Gateway Agent — Phase 11.

Run from the backend directory so the existing connector package is importable.

The agent only initiates outbound HTTP(S) connections to the cloud platform.
Local DB credentials remain in the agent config file and are never uploaded.
"""
import argparse
import json
import os
import platform
import socket
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from connectors.postgresql import PostgreSQLConnector
from connectors.sqlserver import SQLServerConnector
from connectors.query_plan import compile_select_plan, capabilities_for_engine


AGENT_VERSION = "1.0.0"

CONNECTORS = {
    "POSTGRESQL": PostgreSQLConnector,
    "SQLSERVER": SQLServerConnector,
}


def json_default(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, bytes):
        return value.hex()
    return str(value)


def api_request(base_url, path, method="GET", payload=None, token=None):
    url = base_url.rstrip("/") + path
    data = None
    headers = {"Content-Type": "application/json", "User-Agent": f"BI-Gateway/{AGENT_VERSION}"}
    if payload is not None:
        data = json.dumps(payload, default=json_default).encode("utf-8")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status == 204:
                return None
            raw = response.read()
            return json.loads(raw.decode("utf-8")) if raw else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc


def resolve_env_values(value):
    if isinstance(value, dict):
        return {k: resolve_env_values(v) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve_env_values(v) for v in value]
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        env_name = value[2:-1]
        if env_name not in os.environ:
            raise ValueError(f"Environment variable not configured: {env_name}")
        return os.environ[env_name]
    return value


def load_config(path):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return resolve_env_values(raw)


def save_config(path, config):
    Path(path).write_text(
        json.dumps(config, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def connector_for(job, config):
    connection_name = job["data_source"]["local_connection_name"]
    local = config.get("connections", {}).get(connection_name)
    if not local:
        raise ValueError(f"Local connection not configured: {connection_name}")

    expected_engine = job["data_source"]["engine"]
    engine = local.get("engine")
    if engine != expected_engine:
        raise ValueError(
            f"Engine mismatch for {connection_name}: expected {expected_engine}, got {engine}"
        )

    connector_cls = CONNECTORS.get(engine)
    if not connector_cls:
        raise ValueError(f"Unsupported local connector engine: {engine}")

    connector_config = dict(local.get("config") or {})
    return connector_cls(connector_config)


def placeholders(engine, count):
    token = "?" if engine == "SQLSERVER" else "%s"
    return ", ".join([token] * count)


def structured_write(connector, engine, operation, payload):
    schema = payload["schema"]
    table = payload["table"]
    q = connector.quote_identifier
    qualified = f"{q(schema)}.{q(table)}"

    with connector.connection() as conn:
        cursor = conn.cursor()

        if operation == "INSERT":
            values = payload.get("values") or {}
            if not values:
                raise ValueError("INSERT requires values.")
            columns = list(values)
            sql = (
                f"INSERT INTO {qualified} "
                f"({', '.join(q(c) for c in columns)}) "
                f"VALUES ({placeholders(engine, len(columns))})"
            )
            cursor.execute(sql, [values[c] for c in columns])
            affected = cursor.rowcount

        elif operation in {"UPDATE", "DELETE"}:
            where = payload.get("where") or {}
            if not where:
                raise ValueError(f"{operation} requires a non-empty where object.")

            where_cols = list(where)
            where_sql = " AND ".join(
                f"{q(c)} = {'?' if engine == 'SQLSERVER' else '%s'}"
                for c in where_cols
            )
            where_params = [where[c] for c in where_cols]

            if operation == "UPDATE":
                values = payload.get("values") or {}
                if not values:
                    raise ValueError("UPDATE requires values.")
                columns = list(values)
                assignment = ", ".join(
                    f"{q(c)} = {'?' if engine == 'SQLSERVER' else '%s'}"
                    for c in columns
                )
                sql = f"UPDATE {qualified} SET {assignment} WHERE {where_sql}"
                cursor.execute(
                    sql,
                    [values[c] for c in columns] + where_params,
                )
            else:
                sql = f"DELETE FROM {qualified} WHERE {where_sql}"
                cursor.execute(sql, where_params)

            affected = cursor.rowcount
        else:
            raise ValueError(f"Unsupported write operation: {operation}")

        conn.commit()
        return {"affected_rows": int(affected if affected is not None else 0)}


def execute_job(job, config):
    connector = connector_for(job, config)
    operation = job["operation"]
    payload = job.get("payload") or {}

    if operation == "TEST_CONNECTION":
        return connector.test_connection()

    if operation == "CATALOG":
        catalog = connector.introspect_catalog(
            schemas=payload.get("schemas"),
            include_views=payload.get("include_views", True),
        )
        return {
            "tables": [table.to_dict() for table in catalog],
            "count": len(catalog),
        }

    if operation == "READ_PAGE":
        return connector.read_page(
            schema=payload["schema"],
            table=payload["table"],
            columns=payload.get("columns"),
            limit=min(int(payload.get("limit", 100)), 1000),
            offset=max(int(payload.get("offset", 0)), 0),
            cursor_field=payload.get("cursor_field"),
            cursor_gt=payload.get("cursor_gt"),
        )

    if operation == "QUERY_PLAN":
        # The cloud sends a structured, catalog-validated plan; the agent compiles
        # it locally so no arbitrary SQL crosses the private-network boundary.
        query, params = compile_select_plan(payload["plan"], job["data_source"]["engine"])
        return connector.execute_select(query, params)

    if operation in {"INSERT", "UPDATE", "DELETE"}:
        return structured_write(
            connector,
            job["data_source"]["engine"],
            operation,
            payload,
        )

    raise ValueError(f"Unsupported gateway operation: {operation}")


def agent_metadata():
    return {
        "agent_version": AGENT_VERSION,
        "platform": platform.platform(),
        "hostname": socket.gethostname(),
        "capabilities": {
            "operations": [
                "TEST_CONNECTION",
                "CATALOG",
                "READ_PAGE",
                "QUERY_PLAN",
                "INSERT",
                "UPDATE",
                "DELETE",
            ],
            "engines": sorted(CONNECTORS),
            "query_pushdown": {engine: capabilities_for_engine(engine) for engine in sorted(CONNECTORS)},
            "outbound_only": True,
        },
        "metrics": {
            "pid": os.getpid(),
            "python": sys.version.split()[0],
        },
    }


def enroll(config_path, gateway_id, enrollment_code):
    config = load_config(config_path)
    result = api_request(
        config["platform_url"],
        "/api/v1/gateway/agent/enroll/",
        method="POST",
        payload={
            "gateway_id": gateway_id,
            "enrollment_code": enrollment_code,
            **agent_metadata(),
        },
    )
    config["gateway_id"] = result["gateway_id"]
    config["agent_token"] = result["agent_token"]
    save_config(config_path, config)
    print(f"Gateway enrolled. token_version={result['token_version']}")


def rotate_token(config_path):
    config = load_config(config_path)
    result = api_request(
        config["platform_url"],
        "/api/v1/gateway/agent/token/rotate/",
        method="POST",
        payload={},
        token=config["agent_token"],
    )
    config["agent_token"] = result["agent_token"]
    save_config(config_path, config)
    print(f"Token rotated. token_version={result['token_version']}")


def run(config_path):
    config = load_config(config_path)
    poll_seconds = max(1, int(config.get("poll_seconds", 3)))
    heartbeat_seconds = max(10, int(config.get("heartbeat_seconds", 30)))
    last_heartbeat = 0.0

    print("Customer Data Gateway started.")
    print("Outbound mode only. Press Ctrl+C to stop.")

    while True:
        config = load_config(config_path)
        base_url = config["platform_url"]
        token = config["agent_token"]

        now = time.monotonic()
        if now - last_heartbeat >= heartbeat_seconds:
            api_request(
                base_url,
                "/api/v1/gateway/agent/heartbeat/",
                method="POST",
                payload=agent_metadata(),
                token=token,
            )
            last_heartbeat = now

        try:
            job = api_request(
                base_url,
                "/api/v1/gateway/agent/jobs/claim/",
                method="POST",
                payload={},
                token=token,
            )
        except Exception as exc:
            print(f"[gateway] claim error: {exc}", file=sys.stderr)
            time.sleep(min(poll_seconds * 2, 30))
            continue

        if not job:
            time.sleep(poll_seconds)
            continue

        print(f"[gateway] job {job['job_id']} {job['operation']}")
        try:
            result = execute_job(job, config)
            payload = {"success": True, "result": result}
        except Exception as exc:
            payload = {
                "success": False,
                "result": {},
                "error_message": f"{exc.__class__.__name__}: {exc}",
            }

        try:
            api_request(
                base_url,
                f"/api/v1/gateway/agent/jobs/{job['job_id']}/complete/",
                method="POST",
                payload=payload,
                token=token,
            )
        except Exception as exc:
            print(
                f"[gateway] could not report job {job['job_id']}: {exc}",
                file=sys.stderr,
            )


def main():
    parser = argparse.ArgumentParser(description="Business Intelligence Customer Data Gateway")
    parser.add_argument("--config", default="gateway_config.json")
    sub = parser.add_subparsers(dest="command", required=True)

    enroll_parser = sub.add_parser("enroll")
    enroll_parser.add_argument("--gateway-id", required=True)
    enroll_parser.add_argument("--code", required=True)

    sub.add_parser("run")
    sub.add_parser("rotate-token")

    args = parser.parse_args()

    if args.command == "enroll":
        enroll(args.config, args.gateway_id, args.code)
    elif args.command == "rotate-token":
        rotate_token(args.config)
    else:
        run(args.config)


if __name__ == "__main__":
    main()
