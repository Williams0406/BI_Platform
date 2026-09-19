"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import Alert from "@/components/ui/Alert";
import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";
import ExecutionStatus from "@/components/logic/ExecutionStatus";
import PrepareTabs from "@/components/prepare/PrepareTabs";
import { useWorkspace } from "@/lib/hooks/useWorkspace";
import { cancelExecution, listExecutions } from "@/lib/services/executions";
import { getApiErrorMessage } from "@/lib/utils/errors";

const STATUSES = ["", "QUEUED", "RUNNING", "SUCCESS", "FAILED", "CANCELLED", "BLOCKED"];
const TYPES = ["", "SQL_TRANSFORMATION", "PYTHON_TRANSFORMATION", "ML_TRAINING", "ML_INFERENCE", "OPTIMIZATION", "IMPORT", "EXPORT", "DEPENDENCY_PROPAGATION", "GENERIC"];

export default function ExecutionsPage() {
  const { activeWorkspace } = useWorkspace();
  const [items, setItems] = useState([]);
  const [status, setStatus] = useState("");
  const [objectType, setObjectType] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load(silent = false) {
    if (!activeWorkspace?.id) { setItems([]); setLoading(false); return; }
    if (!silent) setLoading(true);
    setError("");
    try {
      const data = await listExecutions({ workspace: activeWorkspace.id, status, objectType });
      setItems(Array.isArray(data) ? data : data.results || []);
    } catch (requestError) { setError(getApiErrorMessage(requestError)); }
    finally { if (!silent) setLoading(false); }
  }

  useEffect(() => { load(); }, [activeWorkspace?.id, status, objectType]);
  useEffect(() => {
    if (!activeWorkspace?.id) return;
    const timer = window.setInterval(() => load(true), 4000);
    return () => window.clearInterval(timer);
  }, [activeWorkspace?.id, status, objectType]);

  async function cancel(item) {
    if (!window.confirm("¿Solicitar cancelación de esta ejecución?")) return;
    try { await cancelExecution(item.id); await load(true); }
    catch (requestError) { setError(getApiErrorMessage(requestError)); }
  }

  if (!activeWorkspace) return <EmptyState title="Selecciona un workspace" description="Las ejecuciones se filtran por workspace." />;

  return <div className="pageStack">
    <header className="pageHeader pageHeaderActions"><div><p className="eyebrow">Prepare</p><h1>Activity</h1><p>Follow running and completed jobs across transformations, ML, optimization, imports and exports.</p></div><button type="button" className="button secondaryButton" onClick={() => load()}>Recargar</button></header>
    <PrepareTabs />{error && <Alert type="error">{error}</Alert>}
    <section className="card"><div className="formGrid twoColumns"><label className="field"><span>Status</span><select value={status} onChange={(e) => setStatus(e.target.value)}>{STATUSES.map((value) => <option key={value} value={value}>{value || "Todos"}</option>)}</select></label><label className="field"><span>Object type</span><select value={objectType} onChange={(e) => setObjectType(e.target.value)}>{TYPES.map((value) => <option key={value} value={value}>{value || "Todos"}</option>)}</select></label></div></section>
    <section className="card">{loading ? <Spinner label="Cargando ejecuciones..." /> : items.length === 0 ? <EmptyState title="Sin ejecuciones" description="Los jobs aparecerán cuando ejecutes transformaciones y otros engines." /> : <div className="tableWrap"><table className="dataTable"><thead><tr><th>Fecha</th><th>Tipo</th><th>Status</th><th>Progreso</th><th>Queue</th><th>Duración</th><th>Acciones</th></tr></thead><tbody>{items.map((item) => <tr key={item.id}><td>{dateTime(item.queued_at)}</td><td>{item.object_type}</td><td><ExecutionStatus status={item.status} /></td><td><div className="miniProgress"><span style={{ width: `${item.progress || 0}%` }} /></div><small>{item.progress || 0}%</small></td><td>{item.queue}</td><td>{item.duration_ms == null ? "—" : `${item.duration_ms} ms`}</td><td><div className="tableActions"><Link className="button secondaryButton smallButton" href={`/app/executions/${item.id}`}>Detalle</Link>{["QUEUED", "RUNNING"].includes(item.status) && <button type="button" className="button dangerButton smallButton" onClick={() => cancel(item)}>Cancelar</button>}</div></td></tr>)}</tbody></table></div>}</section>
  </div>;
}

function dateTime(value) { return value ? new Date(value).toLocaleString() : "—"; }
