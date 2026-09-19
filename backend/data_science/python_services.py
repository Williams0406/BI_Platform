from django.db import transaction

from datasources.models import DataAsset
from dependencies.models import AssetDependency
from dependencies.services import create_dependency, record_change
from execution.services import mark_running, mark_success, update_progress
from platform_ops.parquet import dataframe_to_parquet_artifact

from .runtime.service import execute_python_transformation_runtime


@transaction.atomic
def persist_python_output(transformation, dataframe):
    key = f"python_outputs/{transformation.id}/latest.parquet"
    artifact_uri = dataframe_to_parquet_artifact(dataframe, key)

    asset = transformation.output_asset
    metadata = {
        "storage": "PARQUET_ARTIFACT",
        "artifact_uri": artifact_uri,
        "artifact_path": artifact_uri,
        "producer": "PYTHON_TRANSFORMATION",
        "producer_id": str(transformation.id),
        "row_count": len(dataframe),
        "columns": list(dataframe.columns),
    }
    if asset is None:
        asset = DataAsset.objects.create(
            workspace=transformation.workspace,
            data_source=None,
            name=transformation.output_name,
            asset_type=DataAsset.AssetType.DATASET,
            status=DataAsset.Status.ACTIVE,
            metadata=metadata,
            created_by=transformation.created_by,
        )
        transformation.output_asset = asset
        transformation.save(update_fields=["output_asset", "updated_at"])
    else:
        asset.status = DataAsset.Status.ACTIVE
        asset.metadata = {**(asset.metadata or {}), **metadata}
        asset.save(update_fields=["status", "metadata", "updated_at"])

    for item in transformation.inputs.select_related("asset").all():
        create_dependency(
            workspace=transformation.workspace,
            upstream=item.asset,
            downstream=asset,
            dependency_type=AssetDependency.DependencyType.CALCULATION,
            refresh_policy=AssetDependency.RefreshPolicy.MARK_STALE,
            metadata={
                "producer_type": "PYTHON_TRANSFORMATION",
                "producer_id": str(transformation.id),
            },
        )

    return asset, artifact_uri


def execute_python_transformation(execution, transformation):
    mark_running(execution)
    update_progress(execution, 10, "Preparando inputs del runtime Python.")
    dataframe, runtime_meta = execute_python_transformation_runtime(transformation)

    update_progress(execution, 70, "Persistiendo resultado Parquet.")
    asset, artifact_uri = persist_python_output(transformation, dataframe)

    event = record_change(
        asset,
        "REFRESH",
        user=execution.requested_by,
        metadata={
            "execution_id": str(execution.id),
            "transformation_id": str(transformation.id),
        },
    )
    result = {
        "output_asset_id": str(asset.id),
        "artifact_uri": artifact_uri,
        "rows": int(runtime_meta["rows"]),
        "columns": runtime_meta["columns"],
        "change_event_id": str(event.id),
        "runtime_stdout": runtime_meta["stdout"],
    }
    mark_success(execution, result)
    return result
