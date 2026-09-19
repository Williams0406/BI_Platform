"""Governed technical table rename and reference refactoring.

The user-facing technical name is refactored across platform-authored code and
formula stores. Physical tables are renamed only for Platform/MANAGED data;
External/Private sources keep their source-side physical identifier untouched.
"""
import re
from django.db import connection, transaction
from datasources.models import DataSource
from common.models import ScriptBlock
from metrics.models import MetricDefinition
from transformations.models import SQLTransformation
from data_science.models import PythonTransformation
from .models import FieldContentRule, TableAsset
from .table_identity import technical_name as current_technical_name


def _replace_token(text, old, new):
    if not isinstance(text, str) or not text or old == new:
        return text
    # Technical names are identifiers. Avoid changing substrings such as
    # orders_archive when the table `orders` is renamed.
    pattern = rf"(?<![A-Za-z0-9_]){re.escape(old)}(?![A-Za-z0-9_])"
    return re.sub(pattern, new, text)


def _replace_json(value, old, new):
    if isinstance(value, str):
        return _replace_token(value, old, new)
    if isinstance(value, list):
        return [_replace_json(v, old, new) for v in value]
    if isinstance(value, dict):
        return {k: _replace_json(v, old, new) for k, v in value.items()}
    return value


def _normalize(value):
    value = re.sub(r"[^A-Za-z0-9_]+", "_", str(value or "").strip())
    value = re.sub(r"_+", "_", value).strip("_").lower()
    if not value:
        raise ValueError("Technical name is required.")
    if value[0].isdigit():
        value = f"t_{value}"
    return value[:180]


def _refactor_references(workspace_id, old, new):
    for obj in ScriptBlock.objects.filter(workspace_id=workspace_id):
        code = _replace_token(obj.code, old, new)
        context = _replace_json(obj.context, old, new)
        changed=[]
        if code != obj.code: obj.code=code; changed.append("code")
        if context != obj.context: obj.context=context; changed.append("context")
        if changed: obj.save(update_fields=changed+["updated_at"])

    for obj in FieldContentRule.objects.filter(field__table_asset__data_source__workspace_id=workspace_id):
        expression = _replace_token(obj.expression, old, new)
        dependencies = _replace_json(obj.dependencies, old, new)
        changed=[]
        if expression != obj.expression: obj.expression=expression; changed.append("expression")
        if dependencies != obj.dependencies: obj.dependencies=dependencies; changed.append("dependencies")
        if changed: obj.save(update_fields=changed+["updated_at"])

    for obj in MetricDefinition.objects.filter(workspace_id=workspace_id):
        expression = _replace_token(obj.expression, old, new)
        if expression != obj.expression:
            obj.expression=expression; obj.save(update_fields=["expression","updated_at"])

    for obj in SQLTransformation.objects.filter(workspace_id=workspace_id):
        sql = _replace_token(obj.sql, old, new)
        if sql != obj.sql:
            obj.sql=sql; obj.save(update_fields=["sql","updated_at"])

    for obj in PythonTransformation.objects.filter(workspace_id=workspace_id):
        code = _replace_token(obj.code, old, new)
        if code != obj.code:
            obj.code=code; obj.save(update_fields=["code","updated_at"])

    from common.models import ScriptArtifact
    for obj in ScriptArtifact.objects.filter(script_block__workspace_id=workspace_id):
        metadata=_replace_json(obj.metadata,old,new)
        name=_replace_token(obj.name,old,new)
        changed=[]
        if metadata != obj.metadata: obj.metadata=metadata; changed.append("metadata")
        if name != obj.name: obj.name=name; changed.append("name")
        if changed: obj.save(update_fields=changed)

    try:
        from analytics.models import ChartDefinition, DashboardDefinition, DashboardItem, ReportDefinition
        for obj in ChartDefinition.objects.filter(workspace_id=workspace_id):
            config=_replace_json(obj.config,old,new); filters=_replace_json(obj.default_filters,old,new); changed=[]
            if config != obj.config: obj.config=config; changed.append("config")
            if filters != obj.default_filters: obj.default_filters=filters; changed.append("default_filters")
            if changed: obj.save(update_fields=changed)
        for obj in DashboardDefinition.objects.filter(workspace_id=workspace_id):
            layout=_replace_json(obj.layout,old,new); filters=_replace_json(obj.global_filters,old,new); changed=[]
            if layout != obj.layout: obj.layout=layout; changed.append("layout")
            if filters != obj.global_filters: obj.global_filters=filters; changed.append("global_filters")
            if changed: obj.save(update_fields=changed)
        for obj in DashboardItem.objects.filter(dashboard__workspace_id=workspace_id):
            config=_replace_json(obj.config_override,old,new)
            if config != obj.config_override: obj.config_override=config; obj.save(update_fields=["config_override"])
        for obj in ReportDefinition.objects.filter(workspace_id=workspace_id):
            config=_replace_json(obj.config,old,new)
            if config != obj.config: obj.config=config; obj.save(update_fields=["config"])
    except (ImportError, AttributeError):
        pass

    try:
        from views_engine.models import ViewDefinition, ViewFieldBinding, ViewActionRule
        for obj in ViewDefinition.objects.filter(workspace_id=workspace_id):
            changed=[]
            for field in ("config","default_filters","default_ordering"):
                value=_replace_json(getattr(obj,field),old,new)
                if value != getattr(obj,field): setattr(obj,field,value); changed.append(field)
            if changed: obj.save(update_fields=changed)
        for Model in (ViewFieldBinding, ViewActionRule):
            for obj in Model.objects.filter(view__workspace_id=workspace_id):
                for field in ("options","config"):
                    if hasattr(obj,field):
                        value=_replace_json(getattr(obj,field),old,new)
                        if value != getattr(obj,field): setattr(obj,field,value); obj.save(update_fields=[field])
    except (ImportError, AttributeError):
        pass

    # Optimization expressions are structured JSON. Import lazily so this
    # service stays usable if optimization is disabled in a deployment.
    try:
        from optimization.models import OptimizationObjective, OptimizationConstraint
        for obj in OptimizationObjective.objects.filter(model__workspace_id=workspace_id):
            value=_replace_json(obj.expression,old,new)
            if value != obj.expression: obj.expression=value; obj.save(update_fields=["expression"])
        for obj in OptimizationConstraint.objects.filter(model__workspace_id=workspace_id):
            left=_replace_json(obj.left_expression,old,new); right=_replace_json(obj.right_expression,old,new)
            changed=[]
            if left != obj.left_expression: obj.left_expression=left; changed.append("left_expression")
            if right != obj.right_expression: obj.right_expression=right; changed.append("right_expression")
            if changed: obj.save(update_fields=changed)
    except (ImportError, AttributeError):
        pass


@transaction.atomic
def rename_table(table: TableAsset, requested_name: str):
    old = current_technical_name(table)
    new = _normalize(requested_name)
    workspace = table.data_source.workspace
    collision = TableAsset.objects.filter(data_source__workspace=workspace, technical_name=new).exclude(pk=table.pk)
    if collision.exists():
        raise ValueError(f'A table named "{new}" already exists in this workspace.')
    if old == new:
        return table

    table.data_asset.name = new
    asset_fields = ["name", "updated_at"]
    if table.data_source.mode == DataSource.Mode.MANAGED:
        with connection.cursor() as cursor:
            cursor.execute(
                f"ALTER TABLE {connection.ops.quote_name(table.schema_name)}.{connection.ops.quote_name(table.table_name)} "
                f"RENAME TO {connection.ops.quote_name(new)}"
            )
        table.table_name = new
        table.data_asset.physical_name = new
        asset_fields.append("physical_name")
    table.data_asset.save(update_fields=asset_fields)

    table.technical_name = new
    table.save(update_fields=["technical_name", "table_name", "last_synced_at"] if table.data_source.mode == DataSource.Mode.MANAGED else ["technical_name", "last_synced_at"])
    _refactor_references(workspace.id, old, new)
    return table
