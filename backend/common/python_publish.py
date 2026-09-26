import re
from django.db import connection, transaction
from django.utils.text import slugify
from data_model.managed_services import create_managed_table, delete_managed_table
from data_model.models import TableAsset
from datasources.models import DataAsset
from metrics.models import MetricDefinition, SemanticModel
from .models import ScriptArtifact
from .notebook_execution import execute_python, _python_tables_for_code


def _logical_type(series):
    import pandas as pd
    if pd.api.types.is_bool_dtype(series): return {"logical_type":"BOOLEAN"}
    if pd.api.types.is_integer_dtype(series): return {"logical_type":"BIGINT"}
    if pd.api.types.is_float_dtype(series): return {"logical_type":"DECIMAL","numeric_precision":24,"numeric_scale":8}
    if pd.api.types.is_datetime64_any_dtype(series): return {"logical_type":"DATETIME"}
    length=max([len(str(v)) for v in series.dropna().head(1000)] or [1])
    return {"logical_type":"STRING","max_length":min(max(length,32),4000)}


def _safe_name(name):
    value=slugify(name or "python_output").replace("-","_")
    if not value or value[0].isdigit(): value="python_"+value
    return value[:55]


def _base_table(block):
    found=_python_tables_for_code(block.workspace,"\n".join(b.code or "" for b in block.workspace.script_blocks.filter(language="PYTHON")))
    return found[0][1] if found else TableAsset.objects.filter(data_source__workspace=block.workspace).first()


def publish_python_dataframe(block,user,variable_name,df,output_name=None):
    """Persist an already-executed DataFrame without executing the notebook again."""
    name=(output_name or variable_name).strip()
    physical=_safe_name(name)
    prior=block.artifacts.filter(artifact_type=ScriptArtifact.Type.DATASET,name=name,metadata__variable=variable_name).first()
    if prior and prior.object_id:
        old=TableAsset.objects.filter(id=prior.object_id,data_asset__metadata__producer="PYTHON_SCRIPT").first()
        if old: delete_managed_table(old)
        prior.delete()
    else:
        # A variable may move to a different cell while iterating. Replace only
        # a Python-generated table with the same variable/name; never a user table.
        old=(TableAsset.objects.filter(
            data_source__workspace=block.workspace,
            data_asset__metadata__producer="PYTHON_SCRIPT",
            data_asset__metadata__producer_variable=variable_name,
        ).filter(data_asset__name__iexact=name).first())
        if old: delete_managed_table(old)
    fields=[]
    for col in df.columns:
        info=_logical_type(df[col]); fields.append({"name":str(col),"nullable":True,**info})
    built=create_managed_table(workspace=block.workspace,name=physical,display_name=name,fields=fields,primary_key=[],foreign_keys=[],user=user)
    table=built.table_asset
    meta=dict(table.data_asset.metadata or {}); meta.update({"producer":"PYTHON_SCRIPT","producer_id":str(block.id),"producer_variable":variable_name,"lineage":{"script_block_id":str(block.id),"source_table_ids":[str(t.id) for _,t in _python_tables_for_code(block.workspace,block.code or "")]}})
    table.data_asset.metadata=meta; table.data_asset.asset_type=DataAsset.AssetType.DERIVED_TABLE; table.data_asset.save(update_fields=["metadata","asset_type","updated_at"])
    cols=[str(c) for c in df.columns]; q=connection.ops.quote_name

    # Keep the in-memory notebook DataFrame untouched, but make its persisted
    # representation PostgreSQL-safe. Scientific libraries legitimately emit
    # +/- infinity (for example sklearn.metrics.roc_curve uses +inf for the
    # first threshold), while NUMERIC/DECIMAL columns cannot store infinity.
    # Persist non-finite numeric values as SQL NULL instead of coercing them to
    # zero, which would change their mathematical meaning.
    # Convert the persistence copy to object dtype *before* inserting None.
    # With pandas 3.x, assigning an object Series (created by replacing inf with
    # None) back into a float64 slice can raise ``Invalid value ... for dtype
    # float64``.  Normalise each scalar on an object-typed copy instead.
    import math
    import numbers
    import pandas as pd

    clean = df.copy().astype(object)

    def _storage_safe(value):
        if value is None:
            return None
        # numpy floating scalars implement numbers.Real as well.
        if isinstance(value, numbers.Real):
            try:
                if not math.isfinite(float(value)):
                    return None
            except (TypeError, ValueError, OverflowError):
                pass
        try:
            missing = pd.isna(value)
            if isinstance(missing, bool) and missing:
                return None
        except (TypeError, ValueError):
            pass
        return value

    for column in clean.columns:
        clean[column] = clean[column].map(_storage_safe)

    table_sql=f"{q(table.schema_name)}.{q(table.table_name)}"
    # PostgreSQL COPY is dramatically faster than row-wise executemany for large notebook DataFrames.
    if connection.vendor=="postgresql":
        import csv, io
        buffer=io.StringIO()
        clean.to_csv(buffer,index=False,header=False,na_rep="\\N",quoting=csv.QUOTE_MINIMAL)
        buffer.seek(0)
        copy_sql=f"COPY {table_sql} ({', '.join(q(c) for c in cols)}) FROM STDIN WITH (FORMAT CSV, NULL '\\N')"
        with connection.cursor() as cursor:
            raw=getattr(cursor,"cursor",cursor)
            with raw.copy(copy_sql) as copy:
                while True:
                    chunk=buffer.read(1024*1024)
                    if not chunk: break
                    copy.write(chunk)
    else:
        sql=f"INSERT INTO {table_sql} ({', '.join(q(c) for c in cols)}) VALUES ({', '.join(['%s']*len(cols))})"
        with connection.cursor() as cursor:
            batch=[]
            for row in clean.itertuples(index=False,name=None):
                batch.append(tuple(row))
                if len(batch)>=5000: cursor.executemany(sql,batch); batch=[]
            if batch: cursor.executemany(sql,batch)
    artifact=block.artifacts.create(artifact_type=ScriptArtifact.Type.DATASET,name=name,object_type="TABLE",object_id=str(table.id),metadata={"variable":variable_name,"published":True,"lineage":meta["lineage"]})
    return {"output_type":"DATASET","dataset":{"id":str(table.id),"name":name,"rows":len(df),"fields":cols},"artifact_id":str(artifact.id)}


@transaction.atomic
def publish_python_variable(block,user,variable_name,output_name=None,environment_id=None):
    if block.language.upper()!="PYTHON": raise ValueError("Only Python variables can be published here.")
    captured=execute_python(block,environment_id,capture_variable=variable_name)
    name=(output_name or variable_name).strip()
    if captured["kind"]=="scalar":
        table=_base_table(block)
        if not table: raise ValueError("A base table is required to publish a scalar as a Measure.")
        model=SemanticModel.objects.filter(workspace=block.workspace,base_table=table).first()
        if not model: model=SemanticModel.objects.create(workspace=block.workspace,name=f"{table.technical_name or table.table_name} model",base_table=table,created_by=user)
        metric=MetricDefinition.objects.filter(workspace=block.workspace,name__iexact=name).first()
        value=captured["value"]
        values=dict(semantic_model=model,name=name,expression_type=MetricDefinition.ExpressionType.SQL,expression=str(value).lower() if isinstance(value,bool) else repr(value),aggregation=MetricDefinition.Aggregation.NONE,enabled=True)
        if metric:
            for k,v in values.items(): setattr(metric,k,v)
            metric.save()
        else: metric=MetricDefinition.objects.create(workspace=block.workspace,created_by=user,**values)
        asset,_=DataAsset.objects.update_or_create(workspace=block.workspace,name=name,asset_type=DataAsset.AssetType.METRIC,defaults={"data_source":table.data_source,"status":DataAsset.Status.ACTIVE,"metadata":{"semantic_model_id":str(model.id),"metric_id":str(metric.id),"script_block_id":str(block.id),"producer":"PYTHON_SCRIPT"},"created_by":user})
        if metric.data_asset_id!=asset.id: metric.data_asset=asset; metric.save(update_fields=["data_asset","updated_at"])
        block.artifacts.filter(artifact_type=ScriptArtifact.Type.MEASURE,name=name).delete()
        block.artifacts.create(artifact_type=ScriptArtifact.Type.MEASURE,name=name,object_type="METRIC",object_id=str(metric.id),metadata={"variable":variable_name,"published":True,"lineage":{"script_block_id":str(block.id)}})
        return {"output_type":"MEASURE","measure":{"id":str(metric.id),"name":name,"value":value}}

    df=captured["dataframe"]
    return publish_python_dataframe(block,user,variable_name,df,output_name)
