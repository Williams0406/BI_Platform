from collections import deque

from django.db import transaction
from django.utils import timezone

from datasources.models import DataAsset

from .models import AssetDependency, AssetState, ChangeEvent


class DependencyCycleError(ValueError):
    pass


def ensure_asset_state(asset):
    state, _ = AssetState.objects.get_or_create(asset=asset)
    return state


def _adjacency(workspace_id, exclude_edge_id=None):
    qs = AssetDependency.objects.filter(
        workspace_id=workspace_id,
        active=True,
    )
    if exclude_edge_id:
        qs = qs.exclude(id=exclude_edge_id)

    graph = {}
    for upstream, downstream in qs.values_list("upstream_id", "downstream_id"):
        graph.setdefault(upstream, set()).add(downstream)
    return graph


def would_create_cycle(workspace_id, upstream_id, downstream_id, exclude_edge_id=None):
    if upstream_id == downstream_id:
        return True

    graph = _adjacency(workspace_id, exclude_edge_id=exclude_edge_id)
    graph.setdefault(upstream_id, set()).add(downstream_id)

    # A cycle exists if downstream can reach upstream.
    stack = [downstream_id]
    seen = set()
    while stack:
        node = stack.pop()
        if node == upstream_id:
            return True
        if node in seen:
            continue
        seen.add(node)
        stack.extend(graph.get(node, ()))
    return False


def create_dependency(
    *,
    workspace,
    upstream,
    downstream,
    dependency_type,
    refresh_policy,
    metadata=None,
):
    if upstream.workspace_id != workspace.id or downstream.workspace_id != workspace.id:
        raise ValueError("Los assets deben pertenecer al mismo workspace.")

    if would_create_cycle(workspace.id, upstream.id, downstream.id):
        raise DependencyCycleError("La dependencia crearía un ciclo.")

    dependency, created = AssetDependency.objects.update_or_create(
        upstream=upstream,
        downstream=downstream,
        defaults={
            "workspace": workspace,
            "dependency_type": dependency_type,
            "refresh_policy": refresh_policy,
            "active": True,
            "metadata": metadata or {},
        },
    )
    ensure_asset_state(upstream)
    ensure_asset_state(downstream)
    return dependency, created


def downstream_assets(asset):
    graph = {}
    for upstream, downstream in AssetDependency.objects.filter(
        workspace=asset.workspace,
        active=True,
    ).values_list("upstream_id", "downstream_id"):
        graph.setdefault(upstream, set()).add(downstream)

    ordered = []
    queue = deque(graph.get(asset.id, set()))
    seen = set()

    while queue:
        node = queue.popleft()
        if node in seen:
            continue
        seen.add(node)
        ordered.append(node)
        queue.extend(graph.get(node, set()))

    assets = DataAsset.objects.in_bulk(ordered)
    return [assets[node] for node in ordered if node in assets]


@transaction.atomic
def record_change(asset, change_type, record_key="", user=None, metadata=None):
    state = ensure_asset_state(asset)
    state.version += 1
    state.status = AssetState.Status.FRESH
    state.last_error = ""
    state.save(update_fields=["version", "status", "last_error", "last_changed_at"])

    asset.version = state.version
    asset.save(update_fields=["version", "updated_at"])

    return ChangeEvent.objects.create(
        workspace=asset.workspace,
        asset=asset,
        change_type=change_type,
        record_key=str(record_key or ""),
        metadata=metadata or {},
        created_by=user,
    )


@transaction.atomic
def propagate_change(event):
    dependencies = list(
        AssetDependency.objects.filter(
            workspace=event.workspace,
            upstream=event.asset,
            active=True,
        ).select_related("downstream")
    )

    affected = []

    for dependency in dependencies:
        downstream = dependency.downstream
        state = ensure_asset_state(downstream)

        # AUTO execution is queued by the transformation layer when applicable.
        # Until successfully refreshed, the derived asset is stale.
        state.status = AssetState.Status.STALE
        state.save(update_fields=["status", "last_changed_at"])
        affected.append(
            {
                "asset_id": str(downstream.id),
                "asset": downstream.name,
                "policy": dependency.refresh_policy,
            }
        )

    event.propagated_at = timezone.now()
    event.save(update_fields=["propagated_at"])
    return affected


def lineage(asset):
    upstream = AssetDependency.objects.filter(
        downstream=asset,
        active=True,
    ).select_related("upstream")

    downstream = AssetDependency.objects.filter(
        upstream=asset,
        active=True,
    ).select_related("downstream")

    return {
        "asset": {
            "id": str(asset.id),
            "name": asset.name,
            "type": asset.asset_type,
        },
        "upstream": [
            {
                "id": str(edge.upstream_id),
                "name": edge.upstream.name,
                "dependency_type": edge.dependency_type,
                "refresh_policy": edge.refresh_policy,
            }
            for edge in upstream
        ],
        "downstream": [
            {
                "id": str(edge.downstream_id),
                "name": edge.downstream.name,
                "dependency_type": edge.dependency_type,
                "refresh_policy": edge.refresh_policy,
            }
            for edge in downstream
        ],
    }
