"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import Alert from "@/components/ui/Alert";
import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";
import { useWorkspace } from "@/lib/hooks/useWorkspace";
import { listCatalogTables } from "@/lib/services/dataModel";
import { listDataSources } from "@/lib/services/dataSources";
import { createView, deleteView, listViews } from "@/lib/services/views";
import { getApiErrorMessage } from "@/lib/utils/errors";
import WorkspaceCommandBar from "@/components/data/WorkspaceCommandBar";
import Icon from "@/components/ui/Icon";

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
  const router = useRouter();
  const templateHandled = useRef(false);
  const [views, setViews] = useState([]); const [tables, setTables] = useState([]); const [sources, setSources] = useState([]);
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
  useEffect(()=>{
    if(templateHandled.current||isLoading||!tables.length||typeof window==="undefined")return;
    const requested=new URLSearchParams(window.location.search).get("template");
    if(!requested)return;
    const template=TEMPLATES.find(item=>item[0]===requested);
    if(!template)return;
    templateHandled.current=true; start(template);
  },[isLoading,tables.length]);

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
  return <div className="operationsWorkspacePage">
    <WorkspaceCommandBar view="operations">{canWrite&&<button type="button" className="modelIconAction" onClick={()=>start(["TABLE", "+", "Blank", "Empty canvas"])} title="New Operations view" aria-label="New Operations view"><Icon name="plus" size={17}/></button>}</WorkspaceCommandBar>
    <div className="operationsWorkspaceBody">
    {error && <Alert type="error">{error}</Alert>}{message && <Alert type="success">{message}</Alert>}
    <section className="operationsViewsSection">{isLoading ? <Spinner label="Loading views…" /> : views.length === 0 ? <EmptyState title="No operational views yet" description="Start blank or choose a functional template." /> : <div className="ovViewGrid workspaceLibraryGrid">{views.map((view) => <article className="ovViewCard ovViewCardClickable workspaceLibraryCard" key={view.id} role="link" tabIndex={0} onClick={()=>router.push(`/app/views/${view.id}`)} onKeyDown={e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();router.push(`/app/views/${view.id}`)}}}><div className="ovViewCardCopy"><small>OPERATION</small><h3>{view.name}</h3><p>{view.bindings?.length || 0} bound fields · {view.status}</p></div>{canWrite && <button className="ovIconButton danger ovCardDelete" title="Delete" aria-label={`Delete ${view.name}`} onClick={(e)=>{e.stopPropagation();remove(view)}}>×</button>}</article>)}</div>}</section>
    </div>
  </div>;
}
