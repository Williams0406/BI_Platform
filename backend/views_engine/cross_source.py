"""OQP7 bounded cross-source execution.

Each source/table fragment is pushed down independently, materialized as a bounded
row set, cached briefly, then joined in the platform runtime.  This is deliberately
conservative: no source mutation and no unbounded cross-source transfer.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from django.conf import settings
from django.core.cache import cache

from datasources.models import DataSource


class CrossSourceError(ValueError):
    pass


def limits():
    return {
        "max_rows_per_fragment": int(getattr(settings, "OQP_CROSS_SOURCE_MAX_ROWS", 5000)),
        "cache_seconds": int(getattr(settings, "OQP_CROSS_SOURCE_CACHE_SECONDS", 60)),
    }


def cache_key(fragment):
    raw = json.dumps(fragment, sort_keys=True, default=str).encode()
    return "oqp7:" + hashlib.sha256(raw).hexdigest()


def materialize_fragment(fragment, execute):
    key = cache_key(fragment)
    cached = cache.get(key)
    if cached is not None:
        return cached, True
    result = execute(fragment)
    rows = result.get("rows") or []
    max_rows = limits()["max_rows_per_fragment"]
    if len(rows) >= max_rows:
        # At the safety boundary we cannot prove the source result was complete.
        raise CrossSourceError(
            f"Cross-source fragment reached the safety limit of {max_rows} rows. "
            "Add filters, synchronize the table to Platform, or raise OQP_CROSS_SOURCE_MAX_ROWS deliberately."
        )
    cache.set(key, result, timeout=limits()["cache_seconds"])
    return result, False


def _key(row, columns, prefix):
    return tuple(row.get(f"{prefix}__{c}") for c in columns)


def join_rows(left_rows, right_rows, *, left_prefix, right_prefix, pairs):
    left_cols = [p[0] for p in pairs]
    right_cols = [p[1] for p in pairs]
    index = defaultdict(list)
    for row in right_rows:
        index[_key(row, right_cols, right_prefix)].append(row)
    out = []
    for left in left_rows:
        for right in index.get(_key(left, left_cols, left_prefix), []):
            out.append({**left, **right})
    return out


def source_strategy(source):
    return {
        DataSource.Mode.MANAGED: "PLATFORM_SQL_PUSHDOWN",
        DataSource.Mode.EXTERNAL: "EXTERNAL_SQL_PUSHDOWN",
        DataSource.Mode.PRIVATE_GATEWAY: "PRIVATE_GATEWAY_PUSHDOWN",
    }.get(source.mode, "UNSUPPORTED")
