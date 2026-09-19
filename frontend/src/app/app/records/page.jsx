"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";
import { useWorkspace } from "@/lib/hooks/useWorkspace";
import { listDataSources } from "@/lib/services/dataSources";
import { listCatalogTables } from "@/lib/services/dataModel";
import { getApiErrorMessage } from "@/lib/utils/errors";
import Alert from "@/components/ui/Alert";

export default function RecordsPage() {
  const { activeWorkspace } = useWorkspace();
  const [sources, setSources] = useState([]);
  const [tables, setTables] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      if (!activeWorkspace?.id) { setSources([]); setTables([]); return; }
      setIsLoading(true); setError("");
      try {
        const sourceData = await listDataSources(activeWorkspace.id);
        setSources(sourceData);
        const managed = sourceData.filter((source) => source.mode === "MANAGED");
        const tableGroups = await Promise.all(managed.map((source) => listCatalogTables(source.id)));
        setTables(tableGroups.flat().filter((table) => table.object_type === "TABLE"));
      } catch (requestError) { setError(getApiErrorMessage(requestError)); }
      finally { setIsLoading(false); }
    }
    load();
  }, [activeWorkspace?.id]);

  const managedSource = useMemo(() => sources.find((source) => source.mode === "MANAGED"), [sources]);
  if (!activeWorkspace) return <EmptyState title="Selecciona un workspace" description="Records requiere un workspace activo." />;

  return <div className="pageStack">
    <header className="pageHeader pageHeaderActions"><div><p className="eyebrow">Data</p><h1>Records</h1><p>CRUD dinámico sobre tablas administradas del workspace <strong>{activeWorkspace.name}</strong>.</p></div><Link className="button secondaryButton" href="/app/data-model">Data Model</Link></header>
    {error && <Alert type="error">{error}</Alert>}
    <Alert type="info">La API de Records de esta fase opera únicamente sobre tablas MANAGED. Las fuentes EXTERNAL continúan usando Connector Read APIs.</Alert>
    <section className="card"><div className="cardHeader"><div><h2>Tablas disponibles</h2><p>{managedSource ? managedSource.name : "No existe todavía una fuente MANAGED."}</p></div></div>{isLoading ? <Spinner label="Cargando tablas..." /> : tables.length === 0 ? <EmptyState title="No hay tablas MANAGED" description="Crea una tabla desde Data Model Builder para empezar a trabajar con registros." /> : <div className="tableWrap"><table className="dataTable"><thead><tr><th>Tabla</th><th>Campos</th><th>Primary Key</th><th>Optimistic locking</th><th></th></tr></thead><tbody>{tables.map((table) => <tr key={table.id}><td><strong>{table.technical_name||table.table_name}</strong></td><td>{table.fields?.length || 0}</td><td>{(table.primary_key_columns || []).join(", ") || "—"}</td><td>{table.row_version_column || "__row_version"}</td><td><Link className="button secondaryButton smallButton" href={`/app/records/${table.id}`}>Abrir</Link></td></tr>)}</tbody></table></div>}</section>
  </div>;
}
