"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import DataHubTabs from "@/components/data/DataHubTabs";
import DataSourceForm from "@/components/dataSources/DataSourceForm";
import Alert from "@/components/ui/Alert";
import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";
import { useWorkspace } from "@/lib/hooks/useWorkspace";
import { createDataSource, deleteDataSource, listDataSources, updateDataSource } from "@/lib/services/dataSources";
import { createBinding, deleteBinding, listBindings, updateBinding } from "@/lib/services/customerGateway";
import { getApiErrorMessage } from "@/lib/utils/errors";

const WRITE_ROLES = ["OWNER", "ADMIN", "BUILDER"];

export default function DataSourcesPage() {
  const { activeWorkspace, organizations } = useWorkspace();
  const [sources, setSources] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [editing, setEditing] = useState(null);
  const [showForm, setShowForm] = useState(false);

  const currentOrganization = useMemo(
    () => organizations.find((item) => item.id === activeWorkspace?.organization),
    [organizations, activeWorkspace],
  );
  const canWrite = WRITE_ROLES.includes(currentOrganization?.current_user_role);

  async function loadSources() {
    if (!activeWorkspace?.id) { setSources([]); return; }
    setIsLoading(true); setError("");
    try { setSources(await listDataSources(activeWorkspace.id)); }
    catch (requestError) { setError(getApiErrorMessage(requestError)); }
    finally { setIsLoading(false); }
  }

  useEffect(() => { loadSources(); }, [activeWorkspace?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  async function save(submission) {
    const payload = submission?.data_source || submission;
    const requestedBinding = submission?.gateway_binding || null;
    setIsSaving(true); setError(""); setMessage("");
    try {
      const savedSource = editing
        ? await updateDataSource(editing.id, payload)
        : await createDataSource(payload);

      if (savedSource.mode === "PRIVATE_GATEWAY" || editing?.mode === "PRIVATE_GATEWAY") {
        const bindingsResponse = await listBindings();
        const bindings = Array.isArray(bindingsResponse) ? bindingsResponse : (bindingsResponse?.results || []);
        const currentBinding = bindings.find((item) => item.data_source === savedSource.id);

        if (savedSource.mode === "PRIVATE_GATEWAY" && requestedBinding?.gateway && requestedBinding?.local_connection_name) {
          const bindingPayload = {
            gateway: requestedBinding.gateway,
            data_source: savedSource.id,
            local_connection_name: requestedBinding.local_connection_name,
            enabled: true,
          };
          if (currentBinding) await updateBinding(currentBinding.id, bindingPayload);
          else await createBinding(bindingPayload);
        } else if (currentBinding) {
          await deleteBinding(currentBinding.id);
        }
      }

      setMessage(editing ? "Data Source actualizado." : "Data Source conectado.");
      setEditing(null); setShowForm(false); await loadSources();
    } catch (requestError) { setError(getApiErrorMessage(requestError)); }
    finally { setIsSaving(false); }
  }

  async function remove(source) {
    if (!window.confirm(`¿Eliminar el Data Source "${source.name}"?`)) return;
    setError(""); setMessage("");
    try { await deleteDataSource(source.id); setMessage("Data Source eliminado."); await loadSources(); }
    catch (requestError) { setError(getApiErrorMessage(requestError)); }
  }

  if (!activeWorkspace) return <EmptyState title="Selecciona un workspace" description="Data Sources requiere un workspace activo. Crea o selecciona uno desde la barra superior." />;

  return <div className="pageStack dataHubPage">
    <DataHubTabs />

    {error && <Alert type="error">{error}</Alert>}{message && <Alert type="success">{message}</Alert>}
    {!canWrite && <Alert type="info">Tu rol permite consultar las fuentes, pero no crearlas ni modificarlas.</Alert>}

    {showForm && editing && <div className="modalBackdrop"><section className="semanticModal wideModelModal"><div className="packageExplorerHeader"><h2>Edit source</h2><button className="packageRemove" onClick={()=>{setEditing(null);setShowForm(false)}}>×</button></div><DataSourceForm key={editing.id} source={editing} workspaceId={activeWorkspace.id} onSubmit={save} onCancel={() => { setEditing(null); setShowForm(false); }} isSaving={isSaving} /></section></div>}

    <section className="card"><div className="cardHeader responsiveCardHeader"><div><h2>Fuentes registradas</h2></div><Link className="button secondaryButton" href="/app/data-assets">Browse catalog</Link></div>
      {isLoading ? <Spinner label="Cargando fuentes..." /> : sources.length === 0 ? <EmptyState title="No data sources yet" description="No connected sources." /> : <div className="tableWrap"><table className="dataTable"><thead><tr><th>Fuente</th><th>Modo / Motor</th><th>Estado</th><th>Capacidades</th><th>Conexión</th><th>Acciones</th></tr></thead><tbody>{sources.map((source) => {
        const connectionLabel = source.mode === "MANAGED" ? "Platform storage" : source.mode === "PRIVATE_GATEWAY" ? "Gateway" : "Direct connector";
        return <tr key={source.id}><td><strong>{source.name}</strong><span className="tableSecondary">{source.id}</span></td><td>{source.mode}<span className="tableSecondary">{source.engine}</span></td><td><span className={`statusBadge status-${source.status}`}>{source.status}</span></td><td><div className="capabilityList"><span className={source.can_read ? "capabilityOn" : "capabilityOff"}>READ</span><span className={source.can_write ? "capabilityOn" : "capabilityOff"}>WRITE</span><span className={source.can_ddl ? "capabilityOn" : "capabilityOff"}>DDL</span></div></td><td><span className="statusBadge status-ACTIVE">{connectionLabel}</span></td><td><div className="tableActions"><Link className="button smallButton secondaryButton" href={`/app/data-sources/${source.id}`}>Open</Link>{canWrite && <><button type="button" className="button smallButton secondaryButton" onClick={() => { setEditing(source); setShowForm(true); }}>Edit</button><button type="button" className="button smallButton dangerButton" onClick={() => remove(source)}>Delete</button></>}</div></td></tr>;
      })}</tbody></table></div>}
    </section>
  </div>;
}
