"use client";

import { useEffect, useMemo, useState } from "react";

import Alert from "@/components/ui/Alert";
import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";
import DependencyForm from "@/components/logic/DependencyForm";
import PrepareTabs from "@/components/prepare/PrepareTabs";
import LineagePanel from "@/components/logic/LineagePanel";
import { useWorkspace } from "@/lib/hooks/useWorkspace";
import { listDataAssets } from "@/lib/services/dataSources";
import { createDependency, deleteDependency, getLineage, listAssetStates, listChangeEvents, listDependencies } from "@/lib/services/dependencies";
import { getApiErrorMessage } from "@/lib/utils/errors";

const WRITE_ROLES = ["OWNER", "ADMIN", "BUILDER"];

export default function DependenciesPage() {
  const { activeWorkspace, organizations } = useWorkspace();
  const [edges, setEdges] = useState([]);
  const [assets, setAssets] = useState([]);
  const [states, setStates] = useState([]);
  const [events, setEvents] = useState([]);
  const [selectedAsset, setSelectedAsset] = useState("");
  const [lineage, setLineage] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const organization = useMemo(() => organizations.find((item) => item.id === activeWorkspace?.organization), [organizations, activeWorkspace]);
  const canWrite = WRITE_ROLES.includes(organization?.current_user_role);
  const assetIds = useMemo(() => new Set(assets.map((asset) => asset.id)), [assets]);

  async function load() {
    if (!activeWorkspace?.id) { setLoading(false); return; }
    setLoading(true); setError("");
    try {
      const [edgeData, assetData, stateData, eventData] = await Promise.all([listDependencies(activeWorkspace.id), listDataAssets(activeWorkspace.id), listAssetStates(), listChangeEvents()]);
      const workspaceAssets = Array.isArray(assetData) ? assetData : assetData.results || [];
      const ids = new Set(workspaceAssets.map((asset) => asset.id));
      setAssets(workspaceAssets);
      setEdges(Array.isArray(edgeData) ? edgeData : edgeData.results || []);
      setStates((Array.isArray(stateData) ? stateData : stateData.results || []).filter((state) => ids.has(state.asset)));
      setEvents((Array.isArray(eventData) ? eventData : eventData.results || []).filter((event) => event.workspace === activeWorkspace.id));
    } catch (requestError) { setError(getApiErrorMessage(requestError)); }
    finally { setLoading(false); }
  }

  useEffect(() => { setSelectedAsset(""); setLineage(null); load(); }, [activeWorkspace?.id]);

  async function add(payload) {
    setSaving(true); setError(""); setMessage("");
    try { await createDependency(payload); setMessage("Dependencia creada y validada contra ciclos."); setShowForm(false); await load(); }
    catch (requestError) { setError(getApiErrorMessage(requestError)); }
    finally { setSaving(false); }
  }

  async function remove(edge) {
    if (!window.confirm(`¿Eliminar ${edge.upstream_name} → ${edge.downstream_name}?`)) return;
    try { await deleteDependency(edge.id); setMessage("Dependencia eliminada."); await load(); }
    catch (requestError) { setError(getApiErrorMessage(requestError)); }
  }

  async function inspect(assetId) {
    setSelectedAsset(assetId); setLineage(null); setError("");
    if (!assetId) return;
    try { setLineage(await getLineage(assetId)); }
    catch (requestError) { setError(getApiErrorMessage(requestError)); }
  }

  if (!activeWorkspace) return <EmptyState title="Selecciona un workspace" description="El grafo de dependencias es específico por workspace." />;

  return <div className="pageStack">
    <header className="pageHeader pageHeaderActions"><div><p className="eyebrow">Prepare</p><h1>Lineage</h1><p>Understand what feeds each asset, what depends on it, and whether downstream data is fresh.</p></div>{canWrite && <button type="button" className="button primaryButton" onClick={() => setShowForm(true)}>Nueva dependencia</button>}</header>
    <PrepareTabs />{error && <Alert type="error">{error}</Alert>}{message && <Alert type="success">{message}</Alert>}
    <Alert type="info">La creación de edges valida ciclos en Django. Para cambiar una relación, elimina el edge y crea uno nuevo; así evitamos una actualización que pueda saltarse esa validación.</Alert>
    {showForm && <section className="card"><div className="cardHeader"><div><h2>Nueva dependencia</h2><p>Upstream → Downstream</p></div></div><DependencyForm workspaceId={activeWorkspace.id} assets={assets} onSubmit={add} onCancel={() => setShowForm(false)} isSaving={saving} /></section>}
    <section className="card"><div className="cardHeader"><div><h2>Data flow</h2><p>{edges.length} dependency link(s)</p></div></div>{loading ? <Spinner label="Cargando dependencias..." /> : edges.length === 0 ? <EmptyState title="Sin dependencias" description="Los edges creados manualmente y por transformaciones aparecerán aquí." /> : <div className="dependencyGraph">{edges.map((edge) => <div className="dependencyEdge" key={edge.id}><div><strong>{edge.upstream_name}</strong><small>{edge.dependency_type}</small></div><div className="edgeArrow"><span>→</span><small>{edge.refresh_policy}</small></div><div><strong>{edge.downstream_name}</strong><small>{edge.active ? "ACTIVE" : "INACTIVE"}</small></div>{canWrite && <button type="button" className="button dangerButton smallButton" onClick={() => remove(edge)}>Eliminar</button>}</div>)}</div>}</section>
    <section className="card"><div className="cardHeader"><div><h2>Inspect an asset</h2><p>Follow direct upstream and downstream dependencies.</p></div><select value={selectedAsset} onChange={(e) => inspect(e.target.value)}><option value="">Seleccionar asset...</option>{assets.map((asset) => <option key={asset.id} value={asset.id}>{asset.name} · {asset.asset_type}</option>)}</select></div>{lineage ? <LineagePanel lineage={lineage} /> : <p className="mutedText">Selecciona un asset para inspeccionar su lineage.</p>}</section>
    <section className="card"><div className="cardHeader"><div><h2>Freshness</h2><p>Current dependency state for workspace assets.</p></div></div>{states.length === 0 ? <p className="mutedText">Aún no hay estados registrados.</p> : <div className="tableWrap"><table className="dataTable"><thead><tr><th>Asset</th><th>Status</th><th>Version</th><th>Último cambio</th><th>Último éxito</th><th>Error</th></tr></thead><tbody>{states.map((state) => <tr key={state.asset}><td>{state.asset_name}</td><td><span className={`statusBadge status-${state.status.toLowerCase()}`}>{state.status}</span></td><td>v{state.version}</td><td>{dateTime(state.last_changed_at)}</td><td>{dateTime(state.last_success_at)}</td><td>{state.last_error || "—"}</td></tr>)}</tbody></table></div>}</section>
    <section className="card"><div className="cardHeader"><div><h2>Recent changes</h2><p>Changes that can propagate through the data flow.</p></div></div>{events.length === 0 ? <p className="mutedText">Sin eventos.</p> : <div className="tableWrap"><table className="dataTable"><thead><tr><th>Fecha</th><th>Asset</th><th>Tipo</th><th>Record</th><th>Propagado</th></tr></thead><tbody>{events.slice(0, 50).map((event) => <tr key={event.id}><td>{dateTime(event.created_at)}</td><td>{event.asset_name}</td><td>{event.change_type}</td><td>{event.record_key || "—"}</td><td>{event.propagated_at ? dateTime(event.propagated_at) : "Pendiente"}</td></tr>)}</tbody></table></div>}</section>
  </div>;
}

function dateTime(value) { return value ? new Date(value).toLocaleString() : "—"; }
