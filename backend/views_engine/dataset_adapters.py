"""OQP8 adapters that make UER-produced DataAssets discoverable as datasets."""
from __future__ import annotations

from datasources.models import DataAsset
from data_model.models import TableAsset
from execution.query_ir import dataset_node


def describe_data_asset(asset: DataAsset) -> dict:
    table = TableAsset.objects.filter(data_asset=asset).select_related("data_source").first()
    meta = asset.metadata or {}
    producer = meta.get("producer") or ("ML_PREDICTION" if meta.get("prediction") else "DATA_ASSET")
    result = {
        "asset_id": str(asset.id), "name": asset.name, "asset_type": asset.asset_type,
        "producer": producer, "storage": meta.get("storage") or ("TABLE" if table else "UNKNOWN"),
        "execution_ir": dataset_node(asset_id=asset.id, producer=producer, metadata={"storage": meta.get("storage", "")}),
        "operational_ready": bool(table),
    }
    if table:
        result["table_asset_id"] = str(table.id)
        result["fields"] = list(table.fields.order_by("ordinal_position").values("id", "name", "logical_type"))
    else:
        result["artifact_uri"] = meta.get("artifact_uri") or meta.get("artifact_path") or ""
        result["columns"] = meta.get("columns") or []
        result["note"] = "Artifact dataset is UER-addressable; materialize/catalog it as a Platform table to bind individual Operational fields."
    return result


def list_operational_datasets(workspace):
    return [describe_data_asset(a) for a in DataAsset.objects.filter(workspace=workspace, status=DataAsset.Status.ACTIVE).order_by("name")]
