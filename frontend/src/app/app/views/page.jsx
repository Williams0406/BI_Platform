"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import Alert from "@/components/ui/Alert";
import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";
import { useWorkspace } from "@/lib/hooks/useWorkspace";
import { listCatalogTables } from "@/lib/services/dataModel";
import { listDataSources } from "@/lib/services/dataSources";
import { createView, deleteView, listViews } from "@/lib/services/views";
import { getApiErrorMessage } from "@/lib/utils/errors";

const WRITE_ROLES = ["OWNER", "ADMIN", "BUILDER"];
const TEMPLATES = [
  ["TABLE", "▦", "Table", "Editable operational grid"],
  ["SPREADSHEET", "▦", "Spreadsheet", "Dense editable data workspace"],
  ["FORM", "▤", "Form", "Record entry and editing"],
  ["KANBAN", "▥", "Kanban", "Cards grouped by status"],
  ["CALENDAR", "▣", "Calendar", "Date-driven operational work"],
  ["MATRIX", "⊞", "Matrix", "Cross-tab operational layout"],
];

export default function OperationalViewsPage() {
  const { activeWorkspace, organizations } = useWorkspace();
  const [views, setViews] = useState([]); const [tables, setTables] = useState([]); const [sources, setSources] = useState([]);
  const [creating, setCreating] = useState(false);
  const [isLoading, setIsLoading] = useState(true); const [error, setError] = useState(""); const [message, setMessage] = useState("");
  const organization = useMemo(() => organizations.find((item) => item.id === activeWorkspace?.organization), [organizations, activeWorkspace]);
  const canWrite = WRITE_ROLES.includes(organization?.current_user_role);

  async function load() {
    if (!activeWorkspace?.id) { setIsLoading(false); return; }
    setIsLoading(true); setError("");
    try {
      const [viewData, sourceData] = await Promise.all([listViews({ workspace: activeWorkspace.id }), listDataSources(activeWorkspace.id)]);
      const sourceList = Array.isArray(sourceData) ? sourceData : sourceData.results || [];
      setSources(sourceList); setViews(Array.isArray(viewData) ? viewData : viewData.results || []);
      const groups = await Promise.all(sourceList.map(async (source) => (await listCatalogTables(source.id)).map((table) => ({ ...table, source }))));
      setTables(groups.flat().filter((table) => table.object_type === "TABLE"));
    } catch (requestError) { setError(getApiErrorMessage(requestError)); } finally { setIsLoading(false); }
  }
  useEffect(() => { load(); }, [activeWorkspace?.id]);

  async function start(template) {
    if (!tables.length) { setError("Importa o conecta al menos una tabla antes de crear una Operational View."); return; }
    setError("");
    try {
      // source_table remains a backend compatibility anchor. The builder itself can bind components to any catalog table.
      const anchor = tables[0];
      const created = await createView({ workspace: activeWorkspace.id, source_table: anchor.id, name: "Untitled view", view_type: template[0], status: "ACTIVE", config: { builder_ir: { version: 4, template: template[0], layout: "FREE", components: [], variables: [], actions: [], code: "" } }, default_filters: [], default_ordering: [] });
      window.location.href = `/app/views/${created.id}`;
    } catch (requestError) { setError(getApiErrorMessage(requestError)); }
  }
  async function remove(view) { if (!window.confirm(`¿Eliminar "${view.name}"?`)) return; try { await deleteView(view.id); setMessage("Vista eliminada."); await load(); } catch (e) { setError(getApiErrorMessage(e)); } }

  if (!activeWorkspace) return <EmptyState title="Selecciona un workspace" description="Operational Views pertenece al workspace activo." />;
  return <div className="pageStack">
    <header className="pageHeader pageHeaderActions"><div><p className="eyebrow">Operational apps</p><h1>Operational Views</h1></div>{canWrite && <button className="button primaryButton" onClick={() => setCreating((value) => !value)} title="New view" aria-label="New view">＋</button>}</header>
    {error && <Alert type="error">{error}</Alert>}{message && <Alert type="success">{message}</Alert>}
    {creating && <section className="ovStartStudio"><div className="ovStartHeader"><div><p className="eyebrow">Start building</p><h2>Choose a layout</h2><p>The view is not tied to one table. After opening the canvas, use Data to bind fields from any table available in the workspace.</p></div><button onClick={() => setCreating(false)}>×</button></div><div className="ovTemplateGrid"><button className="ovTemplateCard blank" onClick={() => start(["TABLE", "+", "Blank", "Empty canvas"])}><span>＋</span><strong>Blank canvas</strong><small>Start with data and drag components</small></button>{TEMPLATES.map((template) => <button className="ovTemplateCard" key={template[0]} onClick={() => start(template)}><span>{template[1]}</span><strong>{template[2]}</strong><small>{template[3]}</small></button>)}</div></section>}
    <section className="card"><div className="cardHeader"><div><h2>Views</h2><p>{views.length} operational interface(s)</p></div></div>{isLoading ? <Spinner label="Loading views…" /> : views.length === 0 ? <EmptyState title="No operational views yet" description="Start blank or choose a functional template." /> : <div className="ovViewGrid">{views.map((view) => <article className="ovViewCard" key={view.id}><div className="ovViewPreview"><span>{TEMPLATES.find((item) => item[0] === view.view_type)?.[1] || "◇"}</span></div><div><small>{view.view_type}</small><h3>{view.name}</h3><p>{view.bindings?.length || 0} bound fields · {view.status}</p></div><div><Link className="button primaryButton smallButton" href={`/app/views/${view.id}`} title="Open builder" aria-label="Open builder">↗</Link>{canWrite && <button className="ovIconButton danger" title="Delete" onClick={() => remove(view)}>×</button>}</div></article>)}</div>}</section>
  </div>;
}
