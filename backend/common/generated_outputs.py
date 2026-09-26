"""Lifecycle helpers for analytical outputs owned by Code blocks.

Generated SQL outputs are platform-owned derived artifacts, not user-authored
schema objects. Their cleanup therefore follows ownership, not workspace DDL
permission.
"""
from django.db import connection, transaction
from django.db.models.deletion import ProtectedError

from data_model.models import TableAsset
from datasources.models import DataAsset
from transformations.models import SQLTransformation


def _quote(value):
    return connection.ops.quote_name(value)


def is_script_generated_table(table: TableAsset) -> bool:
    metadata = table.data_asset.metadata or {}
    return metadata.get("producer") in {"SQL_TRANSFORMATION", "PYTHON_SCRIPT"} and bool(metadata.get("producer_id"))


class GeneratedOutputInUseError(Exception):
    """Raised when a generated dataset has become an input to another durable asset."""

    def __init__(self, message, *, dependencies=None):
        super().__init__(message)
        self.dependencies = dependencies or []


def _durable_dependencies(table: TableAsset):
    """Return Data Science consumers of a generated table."""
    dependencies = []
    from data_science.models import DatasetDefinition
    datasets = DatasetDefinition.objects.filter(source_table=table).prefetch_related("models")
    for dataset in datasets:
        models = list(dataset.models.all())
        if models:
            for model in models:
                dependencies.append({"type": "ML_MODEL", "id": str(model.id), "name": model.name})
        else:
            dependencies.append({"type": "DATASET", "id": str(dataset.id), "name": dataset.name})
    return dependencies


def _delete_data_science_tree(table: TableAsset):
    """Delete Data Science artifacts derived from ``table`` before deleting it.

    DatasetDefinition -> ModelDefinition -> ModelRun/ModelVersion is already a
    Django CASCADE chain. Model and prediction DataAssets are collected explicitly
    because those relations point *from* the ML records to DataAsset and therefore
    are not removed when the ML records themselves are deleted.
    """
    from common.models import ScriptArtifact
    from data_science.models import DatasetDefinition, PredictionAsset

    datasets = list(
        DatasetDefinition.objects.filter(source_table=table).prefetch_related(
            "models", "models__versions__prediction_assets"
        )
    )
    model_ids = []
    model_asset_ids = []
    prediction_asset_ids = []
    dataset_ids = []

    for dataset in datasets:
        dataset_ids.append(str(dataset.id))
        for model in dataset.models.all():
            model_ids.append(str(model.id))
            if model.data_asset_id:
                model_asset_ids.append(model.data_asset_id)
            for version in model.versions.all():
                for prediction in version.prediction_assets.all():
                    if prediction.data_asset_id:
                        prediction_asset_ids.append(prediction.data_asset_id)

    # Remove generic Code references to models that are about to disappear.
    if model_ids:
        ScriptArtifact.objects.filter(
            object_type="MODEL_DEFINITION", object_id__in=model_ids
        ).delete()

    # Deleting datasets cascades models, runs, versions and their report payloads.
    if dataset_ids:
        DatasetDefinition.objects.filter(id__in=dataset_ids).delete()

    # Clean catalog assets that are not owned by the reverse cascade above.
    owned_asset_ids = list(dict.fromkeys(prediction_asset_ids + model_asset_ids))
    if owned_asset_ids:
        DataAsset.objects.filter(id__in=owned_asset_ids).delete()

    return {
        "deleted_dataset_ids": dataset_ids,
        "deleted_model_ids": model_ids,
        "deleted_model_asset_ids": [str(v) for v in model_asset_ids],
        "deleted_prediction_asset_ids": [str(v) for v in prediction_asset_ids],
    }

def _detach_script_ownership(table: TableAsset, *, producer, producer_id, retained=False):
    """Detach Code ownership without deleting a table that is now shared by another asset."""
    asset = table.data_asset
    from common.models import ScriptBlock
    if producer == "PYTHON_SCRIPT":
        blocks = ScriptBlock.objects.filter(workspace_id=asset.workspace_id, id=producer_id)
    else:
        blocks = ScriptBlock.objects.filter(
            workspace_id=asset.workspace_id,
            linked_object_type="SQL_TRANSFORMATION",
            linked_object_id=str(producer_id),
        )
    for block in blocks:
        block.artifacts.filter(object_type="TABLE", object_id=str(table.id)).delete()
        block.linked_object_type = ""
        block.linked_object_id = ""
        block.status = "SAVED"
        block.save(update_fields=["linked_object_type", "linked_object_id", "status", "updated_at"])

    if retained:
        metadata = dict(asset.metadata or {})
        metadata.pop("producer", None)
        metadata.pop("producer_id", None)
        metadata["retained_from_code_output"] = True
        asset.metadata = metadata
        asset.save(update_fields=["metadata", "updated_at"])


def _drop_physical_output(table: TableAsset):
    schema = table.data_asset.physical_schema or table.schema_name
    physical = table.data_asset.physical_name or table.table_name
    with connection.cursor() as cursor:
        if table.object_type == TableAsset.ObjectType.VIEW:
            cursor.execute(f"DROP VIEW IF EXISTS {_quote(schema)}.{_quote(physical)} CASCADE")
        else:
            cursor.execute(f"DROP TABLE IF EXISTS {_quote(schema)}.{_quote(physical)} CASCADE")


@transaction.atomic
def delete_script_generated_table(table: TableAsset, *, retain_if_referenced=False):
    """Delete a Code-owned derived table/view without requiring DDL permission.

    Generated Code outputs use ownership cleanup: deleting the producing block or
    deleting its generated table also deletes Data Science datasets/models/runs and
    report payloads derived from that table. This cleanup does not require DDL.
    """
    if not is_script_generated_table(table):
        raise ValueError("La tabla no es un resultado generado por Code.")

    asset = table.data_asset
    metadata = asset.metadata or {}
    producer_id = metadata.get("producer_id")
    producer = metadata.get("producer")
    transformation = SQLTransformation.objects.filter(
        id=producer_id, workspace_id=asset.workspace_id,
    ).first() if producer == "SQL_TRANSFORMATION" else None

    # Generated Code outputs own their downstream Data Science experiment tree.
    # Deleting the block/table therefore removes datasets, models, runs, versions
    # and report payloads first, so protected feature/target relations no longer
    # prevent catalog cleanup.
    deleted_data_science = _delete_data_science_tree(table)

    _drop_physical_output(table)
    _detach_script_ownership(table, producer=producer, producer_id=producer_id)

    # Deleting the DataAsset cascades the TableAsset. SQLTransformation keeps a
    # SET_NULL output relation, so it is safe to remove the transformation next.
    try:
        asset.delete()
    except ProtectedError as exc:
        # Defensive fallback for future protected consumers not yet represented
        # by _durable_dependencies: never turn a dependency conflict into HTTP 500.
        raise GeneratedOutputInUseError(
            "This dataset is referenced by another platform asset and cannot be deleted until its dependencies are removed."
        ) from exc
    if transformation:
        transformation.delete()

    return {
        "deleted_table_id": str(table.id),
        "deleted_transformation_id": str(producer_id or ""),
        **deleted_data_science,
    }


@transaction.atomic
def delete_output_for_script(block):
    """Delete a SQL dataset owned by a ScriptBlock, if one exists."""
    python_tables=[]
    for artifact in block.artifacts.filter(object_type="TABLE"):
        table=TableAsset.objects.select_related("data_asset").filter(id=artifact.object_id,data_asset__metadata__producer="PYTHON_SCRIPT",data_asset__metadata__producer_id=str(block.id)).first()
        if table: python_tables.append(table)
    for table in python_tables: delete_script_generated_table(table, retain_if_referenced=True)
    if block.linked_object_type != "SQL_TRANSFORMATION" or not block.linked_object_id:
        return {"deleted_python_tables": len(python_tables)} if python_tables else None
    transformation = SQLTransformation.objects.select_related("output_asset").filter(
        id=block.linked_object_id,
        workspace_id=block.workspace_id,
    ).first()
    if not transformation:
        return None
    asset = transformation.output_asset
    if not asset:
        transformation.delete()
        return None
    table = TableAsset.objects.select_related("data_asset").filter(data_asset=asset).first()
    if not table:
        transformation.delete()
        asset.delete()
        return None
    return delete_script_generated_table(table, retain_if_referenced=True)
