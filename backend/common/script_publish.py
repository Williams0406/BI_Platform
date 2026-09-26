import re
from django.db import transaction
from data_model.models import TableAsset
from metrics.models import MetricDefinition, SemanticModel
from transformations.models import SQLTransformation
from transformations.services import execute_sql_transformation
from execution.services import create_execution
from execution.models import Execution

AGG_RE = re.compile(r"\b(COUNT|SUM|AVG|MIN|MAX)\s*\(", re.I)

def _split_select_list(text):
    parts=[]; start=0; depth=0; quote=None
    for i,ch in enumerate(text):
        if ch in ("'", '"'):
            if quote==ch: quote=None
            elif quote is None: quote=ch
        elif not quote:
            if ch=='(': depth+=1
            elif ch==')': depth=max(0,depth-1)
            elif ch==',' and depth==0:
                parts.append(text[start:i].strip()); start=i+1
    tail=text[start:].strip()
    if tail: parts.append(tail)
    return parts

def _select_body(sql):
    m=re.search(r"\bSELECT\b(.*?)\bFROM\b", sql, re.I|re.S)
    return m.group(1).strip() if m else ""

def _from_name(sql):
    m=re.search(r"\bFROM\s+(?:\"([^\"]+)\"|([A-Za-z_][\w]*))(?:\.(?:\"([^\"]+)\"|([A-Za-z_][\w]*)))?", sql, re.I)
    if not m: return ""
    return (m.group(3) or m.group(4) or m.group(1) or m.group(2) or "").strip()

def _find_table(workspace, sql):
    name=_from_name(sql)
    qs=TableAsset.objects.filter(data_source__workspace=workspace).select_related('data_asset','data_source')
    if name:
        table=(qs.filter(technical_name__iexact=name).first() or qs.filter(table_name__iexact=name).first() or qs.filter(data_asset__physical_name__iexact=name).first() or qs.filter(data_asset__name__iexact=name).first())
        if table: return table
    return qs.first()

def _qualify_source(sql, table):
    name=_from_name(sql)
    if not name: return sql
    schema=table.data_asset.physical_schema or table.schema_name
    physical=table.data_asset.physical_name or table.table_name
    qualified=f'"{schema}"."{physical}"'
    return re.sub(r"(\bFROM\s+)(?:\"[^\"]+\"|[A-Za-z_][\w]*)(?:\.(?:\"[^\"]+\"|[A-Za-z_][\w]*))?", lambda m:m.group(1)+qualified, sql, count=1, flags=re.I)

def _quote_source_fields(sql, table):
    """Quote catalogued source-column references before PostgreSQL executes SQL.

    Imported CSV/Excel columns can contain upper-case letters. PostgreSQL folds
    unquoted identifiers to lower-case, so Machine_Type would otherwise fail
    when the physical column is actually "Machine_Type".
    """
    result = sql
    fields = sorted(table.fields.all(), key=lambda f: len(f.name), reverse=True)
    for field in fields:
        name = field.name
        # Do not touch identifiers already inside double quotes. Replace only a
        # complete identifier token and preserve SQL strings/aliases reasonably.
        pattern = rf'(?<![A-Za-z0-9_".]){re.escape(name)}(?![A-Za-z0-9_"])'
        result = re.sub(pattern, lambda _m, n=name: f'"{n}"', result, flags=re.I)
    return result


def _metric_expression(expr, table):
    # Store field references using the metric engine's portable token syntax.
    # This preserves mixed-case imported column names in PostgreSQL.
    result=expr
    for field in sorted(table.fields.all(), key=lambda f: len(f.name), reverse=True):
        result=re.sub(rf'(?<![A-Za-z0-9_]){re.escape(field.name)}(?![A-Za-z0-9_])', '{{field:'+field.name+'}}', result, flags=re.I)
    return result

def _alias_and_expression(item):
    m=re.match(r"(?s)(.*?)(?:\s+AS\s+|\s+)([A-Za-z_][\w]*)\s*$", item.strip(), re.I)
    if not m: return None, item.strip()
    return m.group(2), m.group(1).strip()

def classify_sql(sql):
    body=_select_body(sql)
    items=_split_select_list(body)
    measures=[]
    for item in items:
        alias,expr=_alias_and_expression(item)
        if alias and AGG_RE.search(expr): measures.append((alias,expr))
    scalar=bool(measures) and len(measures)==len(items) and not re.search(r"\bGROUP\s+BY\b",sql,re.I)
    return ('MEASURES' if scalar else 'DATASET'), measures

@transaction.atomic
def publish_sql_block(block, user):
    workspace=block.workspace; sql=(block.code or '').strip().rstrip(';')
    kind, measures=classify_sql(sql)
    table=_find_table(workspace,sql)
    if not table: raise ValueError('No se encontró una tabla del workspace para el FROM del SQL.')
    block.artifacts.all().delete()
    if kind=='MEASURES':
        model=SemanticModel.objects.filter(workspace=workspace,base_table=table).first()
        if not model:
            model=SemanticModel.objects.create(workspace=workspace,name=f'{table.technical_name or table.table_name} model',base_table=table,created_by=user)
        created=[]
        for alias,expr in measures:
            metric=MetricDefinition.objects.filter(workspace=workspace,name__iexact=alias).first()
            portable_expr=_metric_expression(expr,table)
            values=dict(semantic_model=model,name=alias,expression_type=MetricDefinition.ExpressionType.SQL,expression=portable_expr,aggregation=MetricDefinition.Aggregation.NONE,enabled=True)
            if metric:
                for k,v in values.items(): setattr(metric,k,v)
                metric.save()
            else:
                metric=MetricDefinition.objects.create(workspace=workspace,created_by=user,**values)
            from datasources.models import DataAsset
            asset,_=DataAsset.objects.update_or_create(workspace=workspace,name=metric.name,asset_type=DataAsset.AssetType.METRIC,defaults={'data_source':table.data_source,'status':DataAsset.Status.ACTIVE,'metadata':{'semantic_model_id':str(model.id),'metric_id':str(metric.id),'script_block_id':str(block.id)},'created_by':user})
            if metric.data_asset_id!=asset.id: metric.data_asset=asset; metric.save(update_fields=['data_asset','updated_at'])
            block.artifacts.create(artifact_type='MEASURE',name=alias,object_type='METRIC',object_id=str(metric.id),metadata={'expression':portable_expr,'source_expression':expr,'published':True})
            created.append({'id':str(metric.id),'name':alias})
        block.linked_object_type='METRIC_SET'; block.linked_object_id=''; block.status='APPLIED'; block.save(update_fields=['linked_object_type','linked_object_id','status','updated_at'])
        return {'output_type':'MEASURES','measures':created}
    rendered=_quote_source_fields(_qualify_source(sql,table), table)
    name=f'SQL summary {str(block.id)[:8]}'
    tx=SQLTransformation.objects.filter(workspace=workspace,description__contains=f'script:{block.id}').first()
    if tx:
        tx.sql=rendered; tx.name=name; tx.enabled=True; tx.save(update_fields=['sql','name','enabled','updated_at'])
    else:
        tx=SQLTransformation.objects.create(workspace=workspace,name=name,description=f'Published from Code · script:{block.id}',sql=rendered,output_mode=SQLTransformation.OutputMode.VIEW,refresh_policy=SQLTransformation.RefreshPolicy.MANUAL,enabled=True,created_by=user)
    execution=create_execution(workspace=workspace,object_type=Execution.ObjectType.SQL_TRANSFORMATION,object_id=tx.id,queue='sql',requested_by=user)
    result=execute_sql_transformation(execution)
    # execute_sql_transformation() loads and updates its own SQLTransformation
    # instance. Refresh this instance before resolving the generated catalog table;
    # otherwise tx.output_asset_id is still None on the first publication.
    tx.refresh_from_db(fields=['output_asset'])
    output_asset_id = tx.output_asset_id or result.get('output_asset_id')
    if not output_asset_id:
        raise ValueError('La transformación SQL terminó sin registrar un DataAsset de salida.')
    table_out=(
        TableAsset.objects
        .select_related('data_asset','data_source')
        .prefetch_related('fields')
        .filter(data_asset_id=output_asset_id)
        .first()
    )
    if not table_out:
        raise ValueError('El resultado SQL fue materializado, pero su tabla no quedó registrada en el catálogo.')
    block.artifacts.create(artifact_type='DATASET',name=tx.name,object_type='TABLE',object_id=str(table_out.id),metadata={'transformation_id':str(tx.id),'published':True})
    block.linked_object_type='SQL_TRANSFORMATION'; block.linked_object_id=str(tx.id); block.status='APPLIED'; block.save(update_fields=['linked_object_type','linked_object_id','status','updated_at'])
    return {'output_type':'DATASET','dataset':{'id':str(table_out.id),'name':tx.output_asset.name,'fields':[f.name for f in table_out.fields.all()]},'execution':result}

def publish_block(block,user):
    if block.language.upper()!='SQL':
        return {'output_type':'CODE','detail':'Automatic publishing is currently enabled for SQL blocks.'}
    return publish_sql_block(block,user)
