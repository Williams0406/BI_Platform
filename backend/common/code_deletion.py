"""Delete a measure and its defining blocks together, within one workspace."""
from django.db import transaction

from datasources.models import DataAsset
from metrics.models import MetricDefinition
from .models import ScriptBlock


METRIC_TYPES = {"METRIC", "MEASURE", "METRIC_DEFINITION"}


def block_metric_ids(block, metrics):
    """Prefer ownership IDs; support exact, unambiguous legacy definitions."""
    ids = set()
    if block.linked_object_type.upper() in METRIC_TYPES:
        ids.add(str(block.linked_object_id))
    for artifact in block.artifacts.all():
        if artifact.object_type.upper() in METRIC_TYPES:
            ids.add(str(artifact.object_id))
    if ids or block.linked_object_type:
        return ids & metrics.keys()
    # Older notebook blocks have no object IDs. Match a full definition and
    # its expression, not just a same-named artifact or a reference to it.
    source = block.code.strip()
    table_id = (block.context or {}).get("table_id")
    names = {block.name} | {a.name for a in block.artifacts.all() if a.artifact_type == "MEASURE"}
    candidates = []
    for key, metric in metrics.items():
        if metric.expression_type != block.language or not metric.expression.strip():
            continue
        if table_id and str(metric.semantic_model.base_table_id) != str(table_id):
            continue
        definition = f"{metric.name} = {metric.expression.strip()}"
        if source in {definition, f"MEASURE {definition}"} or (metric.name in names and source == metric.expression.strip()):
            candidates.append(key)
    return set(candidates) if len(candidates) == 1 else set()


@transaction.atomic
def delete_code_and_measures(*, workspace_id, script_id=None, metric_id=None):
    # Locks serialize concurrent deletions/updates of the same records.
    metrics = {str(m.id): m for m in MetricDefinition.objects.select_for_update().select_related("semantic_model").filter(workspace_id=workspace_id)}
    blocks = {str(b.id): b for b in ScriptBlock.objects.select_for_update().filter(workspace_id=workspace_id).prefetch_related("artifacts")}
    links = {key: block_metric_ids(block, metrics) for key, block in blocks.items()}
    deleted_blocks = {str(script_id)} & blocks.keys() if script_id else set()
    deleted_metrics = {str(metric_id)} & metrics.keys() if metric_id else set()
    # Multiple historical blocks can own the same measure; a block can own
    # several measures. Remove the whole connected ownership group.
    while True:
        before = (len(deleted_blocks), len(deleted_metrics))
        for key, owned in links.items():
            if key in deleted_blocks or owned & deleted_metrics:
                deleted_blocks.add(key)
                deleted_metrics.update(owned)
        if before == (len(deleted_blocks), len(deleted_metrics)):
            break
    # SQL blocks own their derived dataset/view. Remove that platform-owned
    # output as part of deleting the defining block; this is ownership cleanup,
    # not arbitrary user DDL.
    if script_id and str(script_id) in blocks:
        from .generated_outputs import delete_output_for_script
        delete_output_for_script(blocks[str(script_id)])

    result = {
        "workspace": str(workspace_id),
        "deleted_script_ids": sorted(deleted_blocks),
        "deleted_metric_ids": sorted(deleted_metrics),
        "deleted_code": [{"code": blocks[key].code, "language": blocks[key].language} for key in deleted_blocks],
    }
    # Include editor representations so browser drafts are removed as well.
    for key in deleted_metrics:
        metric = metrics[key]
        result["deleted_code"].extend([
            {"code": metric.expression, "language": metric.expression_type},
            {"code": f"{metric.name} = {metric.expression}", "language": metric.expression_type},
        ])
    asset_ids = [metrics[key].data_asset_id for key in deleted_metrics if metrics[key].data_asset_id]
    ScriptBlock.objects.filter(id__in=deleted_blocks, workspace_id=workspace_id).delete()
    MetricDefinition.objects.filter(id__in=deleted_metrics, workspace_id=workspace_id).delete()
    DataAsset.objects.filter(id__in=asset_ids, workspace_id=workspace_id, asset_type="METRIC").delete()
    return result
