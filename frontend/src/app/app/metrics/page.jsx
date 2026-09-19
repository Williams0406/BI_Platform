"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import SemanticModelForm from "@/components/metrics/SemanticModelForm";
import MetricForm from "@/components/metrics/MetricForm";
import Alert from "@/components/ui/Alert";
import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";
import { useWorkspace } from "@/lib/hooks/useWorkspace";
import { listCatalogTables } from "@/lib/services/dataModel";
import { listDataSources } from "@/lib/services/dataSources";
import {
  createMetric,
  createSemanticModel,
  deleteMetric,
  deleteSemanticModel,
  listMetrics,
  listSemanticModels,
  updateMetric,
  updateSemanticModel,
} from "@/lib/services/metrics";
import { getApiErrorMessage } from "@/lib/utils/errors";

const WRITE_ROLES = ["OWNER", "ADMIN", "BUILDER"];

function listValue(data) { return Array.isArray(data) ? data : data?.results || []; }

export default function MetricsPage() {
  const { activeWorkspace, organizations } = useWorkspace();
  const [models, setModels] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [tables, setTables] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [modelForm, setModelForm] = useState(false);
  const [metricForm, setMetricForm] = useState(false);
  const [editingModel, setEditingModel] = useState(null);
  const [editingMetric, setEditingMetric] = useState(null);
  const [saving, setSaving] = useState(false);

  const organization = useMemo(() => organizations.find((item) => item.id === activeWorkspace?.organization), [organizations, activeWorkspace]);
  const canWrite = WRITE_ROLES.includes(organization?.current_user_role);
  const tablesById = useMemo(() => Object.fromEntries(tables.map((table) => [table.id, table])), [tables]);

  async function load() {
    if (!activeWorkspace?.id) { setLoading(false); setModels([]); setMetrics([]); setTables([]); return; }
    setLoading(true); setError("");
    try {
      const [modelData, metricData, sourceData, tableData] = await Promise.all([
        listSemanticModels(activeWorkspace.id),
        listMetrics(activeWorkspace.id),
        listDataSources(activeWorkspace.id),
        listCatalogTables(),
      ]);
      const sources = listValue(sourceData);
      const managedIds = new Set(sources.filter((item) => item.mode === "MANAGED").map((item) => item.id));
      setModels(listValue(modelData));
      setMetrics(listValue(metricData));
      setTables(listValue(tableData).filter((table) => managedIds.has(table.data_source) && table.object_type === "TABLE"));
    } catch (requestError) { setError(getApiErrorMessage(requestError)); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, [activeWorkspace?.id]);

  async function saveModel(payload) {
    setSaving(true); setError(""); setMessage("");
    try {
      if (editingModel) { await updateSemanticModel(editingModel.id, payload); setMessage("Semantic Model actualizado."); }
      else { await createSemanticModel(payload); setMessage("Semantic Model creado."); }
      setModelForm(false); setEditingModel(null); await load();
    } catch (requestError) { setError(getApiErrorMessage(requestError)); }
    finally { setSaving(false); }
  }

  async function saveMetric(payload) {
    setSaving(true); setError(""); setMessage("");
    try {
      if (editingMetric) { await updateMetric(editingMetric.id, payload); setMessage("Métrica actualizada."); }
      else { await createMetric(payload); setMessage("Métrica creada y Data Asset asociado generado."); }
      setMetricForm(false); setEditingMetric(null); await load();
    } catch (requestError) { setError(getApiErrorMessage(requestError)); }
    finally { setSaving(false); }
  }

  async function removeModel(item) {
    if (!window.confirm(`¿Eliminar el Semantic Model "${item.name}"? Sus dimensiones y métricas relacionadas pueden verse afectadas.`)) return;
    try { await deleteSemanticModel(item.id); setMessage("Semantic Model eliminado."); await load(); }
    catch (requestError) { setError(getApiErrorMessage(requestError)); }
  }
  async function removeMetric(item) {
    if (!window.confirm(`¿Eliminar la métrica "${item.name}"?`)) return;
    try { await deleteMetric(item.id); setMessage("Métrica eliminada."); await load(); }
    catch (requestError) { setError(getApiErrorMessage(requestError)); }
  }

  if (!activeWorkspace) return <EmptyState title="Selecciona un workspace" description="La capa semántica pertenece a un workspace." />;

  return <div className="pageStack">
    <header className="pageHeader pageHeaderActions"><div><p className="eyebrow">Semantic Layer</p><h1>Metrics</h1><p>Define modelos semánticos, dimensiones y métricas reutilizables para Analytics, Dashboards y Reports.</p></div><div className="headerActions">{canWrite&&<><button type="button" className="button secondaryButton" onClick={()=>{setEditingModel(null);setModelForm(true);}}>Nuevo Semantic Model</button><button type="button" className="button primaryButton" onClick={()=>{setEditingMetric(null);setMetricForm(true);}} disabled={!models.length}>Nueva métrica</button></>}</div></header>
    {error&&<Alert type="error">{error}</Alert>}{message&&<Alert type="success">{message}</Alert>}
    <Alert type="info">Las consultas de métricas se ejecutan en PostgreSQL de la plataforma. Por seguridad funcional, esta UI usa únicamente tablas <strong>MANAGED</strong> como base semántica.</Alert>

    {modelForm&&<section className="card"><div className="cardHeader"><div><h2>{editingModel?"Editar Semantic Model":"Nuevo Semantic Model"}</h2><p>Un modelo semántico define la tabla base que compartirán dimensiones y métricas.</p></div></div><SemanticModelForm workspaceId={activeWorkspace.id} tables={tables} initialValue={editingModel} onSubmit={saveModel} onCancel={()=>{setModelForm(false);setEditingModel(null);}} isSaving={saving}/></section>}
    {metricForm&&<section className="card"><div className="cardHeader"><div><h2>{editingMetric?"Editar métrica":"Nueva métrica"}</h2><p>Las métricas SIMPLE usan agregaciones estándar; SQL acepta solo expresiones seguras con tokens de campo.</p></div></div><MetricForm workspaceId={activeWorkspace.id} models={models} tablesById={tablesById} initialValue={editingMetric} onSubmit={saveMetric} onCancel={()=>{setMetricForm(false);setEditingMetric(null);}} isSaving={saving}/></section>}

    {loading?<Spinner label="Cargando capa semántica..."/>:<>
      <section className="card"><div className="cardHeader"><div><h2>Semantic Models</h2><p>{models.length} modelo(s)</p></div></div>{models.length===0?<EmptyState title="Sin Semantic Models" description="Crea un modelo sobre una tabla MANAGED antes de definir métricas."/>:<div className="tableWrap"><table className="dataTable"><thead><tr><th>Nombre</th><th>Tabla base</th><th>Dimensiones</th><th>Métricas</th><th>Estado</th><th>Acciones</th></tr></thead><tbody>{models.map(model=><tr key={model.id}><td><strong>{model.name}</strong><div className="mutedText">{model.description||"Sin descripción"}</div></td><td>{tablesById[model.base_table]?tablesById[model.base_table].table_name:String(model.base_table).slice(0,8)}</td><td>{model.dimensions?.length||0}</td><td>{model.metrics?.length||0}</td><td><span className="statusBadge">{model.enabled?"ENABLED":"DISABLED"}</span></td><td><div className="tableActions"><Link className="button secondaryButton smallButton" href={`/app/metrics/models/${model.id}`}>Dimensiones</Link>{canWrite&&<><button type="button" className="button secondaryButton smallButton" onClick={()=>{setEditingModel(model);setModelForm(true);}}>Editar</button><button type="button" className="button dangerButton smallButton" onClick={()=>removeModel(model)}>Eliminar</button></>}</div></td></tr>)}</tbody></table></div>}</section>
      <section className="card"><div className="cardHeader"><div><h2>Metric Definitions</h2><p>{metrics.length} métrica(s)</p></div></div>{metrics.length===0?<EmptyState title="Sin métricas" description="Crea una métrica SIMPLE o SQL sobre un Semantic Model."/>:<div className="tableWrap"><table className="dataTable"><thead><tr><th>Nombre</th><th>Modelo</th><th>Expresión</th><th>Formato</th><th>Cache</th><th>Data Asset</th><th>Acciones</th></tr></thead><tbody>{metrics.map(metric=><tr key={metric.id}><td><strong>{metric.name}</strong><div className="mutedText">{metric.enabled?"Activa":"Deshabilitada"}</div></td><td>{models.find(m=>m.id===metric.semantic_model)?.name||String(metric.semantic_model).slice(0,8)}</td><td>{metric.expression_type==="SIMPLE"?`${metric.aggregation}${metric.source_field_name?`(${metric.source_field_name})`:"(*)"}`:"SQL expression"}</td><td>{metric.format_type}{metric.unit?` · ${metric.unit}`:""}<div className="mutedText">{metric.decimal_places} decimal(es)</div></td><td>{metric.cache_ttl_seconds}s</td><td>{metric.data_asset?String(metric.data_asset).slice(0,8):"—"}</td><td><div className="tableActions"><Link className="button primaryButton smallButton" href={`/app/metrics/${metric.id}`}>Consultar</Link>{canWrite&&<><button type="button" className="button secondaryButton smallButton" onClick={()=>{setEditingMetric(metric);setMetricForm(true);}}>Editar</button><button type="button" className="button dangerButton smallButton" onClick={()=>removeMetric(metric)}>Eliminar</button></>}</div></td></tr>)}</tbody></table></div>}</section>
    </>}
  </div>;
}
