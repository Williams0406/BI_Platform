"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import Alert from "@/components/ui/Alert";
import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";
import { useWorkspace } from "@/lib/hooks/useWorkspace";
import { getDataSource } from "@/lib/services/dataSources";
import { deleteManagedTable, getCatalogTable, listCatalogRelations } from "@/lib/services/dataModel";
import { getApiErrorMessage } from "@/lib/utils/errors";

const WRITE_ROLES = ["OWNER", "ADMIN", "BUILDER"];

export default function DataModelDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { activeWorkspace, organizations } = useWorkspace();
  const [table, setTable] = useState(null);
  const [source, setSource] = useState(null);
  const [relations, setRelations] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  const currentOrganization = useMemo(() => organizations.find((item) => item.id === activeWorkspace?.organization), [organizations, activeWorkspace]);
  const canWrite = WRITE_ROLES.includes(currentOrganization?.current_user_role);
  const isManaged = source?.mode === "MANAGED";

  useEffect(() => {
    async function load() {
      setIsLoading(true); setError("");
      try {
        const tableData = await getCatalogTable(params.id);
        const [sourceData, relationData] = await Promise.all([getDataSource(tableData.data_source), listCatalogRelations(tableData.data_source)]);
        setTable(tableData); setSource(sourceData); setRelations(relationData.filter((item) => item.source_table === tableData.id || item.target_table === tableData.id));
      } catch (requestError) { setError(getApiErrorMessage(requestError)); }
      finally { setIsLoading(false); }
    }
    if (params.id) load();
  }, [params.id]);

  async function remove() {
    if (!window.confirm(`¿Solicitar eliminar ${table.technical_name||table.table_name}?`)) return;
    setError("");
    try { await deleteManagedTable(table.id); router.push("/app/data-model"); }
    catch (requestError) {
      const base = getApiErrorMessage(requestError);
      const requiresApproval = requestError?.response?.data?.requires_approval;
      setError(requiresApproval ? `${base} La eliminación requiere una aprobación de Governance antes de volver a intentarla.` : base);
    }
  }

  if (isLoading) return <Spinner label="Cargando tabla..." />;
  if (!table) return <EmptyState title="Tabla no disponible" description={error || "No se encontró la definición solicitada."} />;

  const simplePk = (table.primary_key_columns || []).length === 1;
  return <div className="pageStack">
    <header className="pageHeader pageHeaderActions"><div><p className="eyebrow">Data Model</p><h1>{table.technical_name||table.table_name}</h1><p>{source?.name} · {source?.mode} · {table.object_type}</p></div><div className="formActions"><Link className="button secondaryButton" href="/app/data-model">Volver</Link>{isManaged && <Link className="button primaryButton" href={`/app/records/${table.id}`}>Abrir registros</Link>}{isManaged && canWrite && <button type="button" className="button dangerButton" onClick={remove}>Eliminar tabla</button>}</div></header>
    {error && <Alert type="error">{error}</Alert>}
    {isManaged && !simplePk && <Alert type="info">La tabla puede listar y crear registros, pero editar/eliminar por fila requiere una PK simple en la API de Fase 4.</Alert>}
    <section className="summaryGrid"><div><span>Object type</span><strong>{table.object_type}</strong></div><div><span>Campos</span><strong>{table.fields?.length || 0}</strong></div><div><span>Primary Key</span><strong>{(table.primary_key_columns || []).join(", ") || "—"}</strong></div><div><span>Row version</span><strong>{table.row_version_column || "—"}</strong></div></section>
    <section className="card"><div className="cardHeader"><div><h2>Campos</h2><p>Definición lógica y física registrada en catálogo.</p></div></div><div className="tableWrap"><table className="dataTable"><thead><tr><th>#</th><th>Campo</th><th>Tipo lógico</th><th>Tipo nativo</th><th>PK</th><th>Nullable</th><th>Identity</th><th>Default</th></tr></thead><tbody>{(table.fields || []).map((field) => <tr key={field.id}><td>{field.ordinal_position}</td><td><strong>{field.business_name || field.name}</strong>{field.business_name && <span className="tableSecondary">{field.name}</span>}</td><td>{field.logical_type}</td><td><code>{field.native_type}</code></td><td>{field.is_primary_key ? "Sí" : "—"}</td><td>{field.nullable ? "Sí" : "No"}</td><td>{field.is_identity ? "Sí" : "—"}</td><td>{field.default_value || "—"}</td></tr>)}</tbody></table></div></section>
    <section className="card"><div className="cardHeader"><div><h2>Relaciones</h2><p>Entrantes y salientes para esta tabla.</p></div></div>{relations.length === 0 ? <p className="mutedText">Sin relaciones.</p> : <div className="tableWrap"><table className="dataTable"><thead><tr><th>Nombre</th><th>Dirección</th><th>Origen</th><th>Destino</th></tr></thead><tbody>{relations.map((relation) => <tr key={relation.id}><td>{relation.name}</td><td>{relation.source_table === table.id ? "Saliente" : "Entrante"}</td><td>{relation.source} ({relation.source_columns.join(", ")})</td><td>{relation.target} ({relation.target_columns.join(", ")})</td></tr>)}</tbody></table></div>}</section>
  </div>;
}
