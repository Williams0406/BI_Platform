"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import RecordFilters from "@/components/records/RecordFilters";
import RecordForm from "@/components/records/RecordForm";
import Alert from "@/components/ui/Alert";
import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";
import { useWorkspace } from "@/lib/hooks/useWorkspace";
import { getCatalogTable } from "@/lib/services/dataModel";
import { createRecord, deleteRecord, listRecords, updateRecord } from "@/lib/services/records";
import { getApiErrorMessage } from "@/lib/utils/errors";

const WRITE_ROLES = ["OWNER", "ADMIN", "BUILDER"];

function formatCell(value) {
  if (value === null || value === undefined) return "NULL";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export default function RecordTablePage() {
  const params = useParams();
  const { activeWorkspace, organizations } = useWorkspace();
  const [table, setTable] = useState(null);
  const [rows, setRows] = useState([]);
  const [limit, setLimit] = useState(25);
  const [offset, setOffset] = useState(0);
  const [returned, setReturned] = useState(0);
  const [orderBy, setOrderBy] = useState("");
  const [filters, setFilters] = useState([]);
  const [appliedFilters, setAppliedFilters] = useState([]);
  const [showFilters, setShowFilters] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const currentOrganization = useMemo(() => organizations.find((item) => item.id === activeWorkspace?.organization), [organizations, activeWorkspace]);
  const canWrite = WRITE_ROLES.includes(currentOrganization?.current_user_role);
  const pkColumns = table?.primary_key_columns || [];
  const simplePk = pkColumns.length === 1;
  const pkField = simplePk ? pkColumns[0] : null;
  const versionColumn = table?.row_version_column || "__row_version";

  async function loadRows(nextOffset = offset, nextFilters = appliedFilters, nextOrder = orderBy, nextLimit = limit) {
    if (!table?.id) return;
    setIsLoading(true); setError("");
    try {
      const data = await listRecords(table.id, { limit: nextLimit, offset: nextOffset, orderBy: nextOrder, filters: nextFilters });
      setRows(data.rows || []); setReturned(data.returned || 0); setOffset(data.offset ?? nextOffset);
    } catch (requestError) { setError(getApiErrorMessage(requestError)); }
    finally { setIsLoading(false); }
  }

  useEffect(() => {
    async function init() {
      setIsLoading(true); setError("");
      try {
        const tableData = await getCatalogTable(params.id);
        setTable(tableData);
        const data = await listRecords(tableData.id, { limit: 25, offset: 0 });
        setRows(data.rows || []); setReturned(data.returned || 0); setOffset(data.offset || 0);
      } catch (requestError) { setError(getApiErrorMessage(requestError)); }
      finally { setIsLoading(false); }
    }
    if (params.id) init();
  }, [params.id]);

  async function save(payload) {
    setIsSaving(true); setError(""); setMessage("");
    try {
      if (editing) {
        await updateRecord(table.id, editing[pkField], payload, editing[versionColumn]);
        setMessage("Registro actualizado correctamente.");
      } else {
        await createRecord(table.id, payload);
        setMessage("Registro creado correctamente.");
      }
      setEditing(null); setShowForm(false); await loadRows();
    } catch (requestError) {
      const status = requestError?.response?.status;
      const text = getApiErrorMessage(requestError);
      setError(status === 409 ? `${text} Se detectó un conflicto de versión; recarga los registros antes de reintentar.` : text);
    } finally { setIsSaving(false); }
  }

  async function remove(row) {
    if (!simplePk) return;
    if (!window.confirm(`¿Eliminar el registro ${row[pkField]}?`)) return;
    setError(""); setMessage("");
    try {
      await deleteRecord(table.id, row[pkField], row[versionColumn]);
      setMessage("Registro eliminado."); await loadRows();
    } catch (requestError) {
      const status = requestError?.response?.status;
      const text = getApiErrorMessage(requestError);
      setError(status === 409 ? `${text} Recarga los registros antes de volver a eliminar.` : text);
    }
  }

  function changeOrder(fieldName) {
    const next = orderBy === fieldName ? `-${fieldName}` : orderBy === `-${fieldName}` ? "" : fieldName;
    setOrderBy(next); setOffset(0); loadRows(0, appliedFilters, next, limit);
  }

  if (!table && isLoading) return <Spinner label="Cargando Records Engine..." />;
  if (!table) return <EmptyState title="Tabla no disponible" description={error || "No se encontró la tabla solicitada."} />;

  return <div className="pageStack">
    <header className="pageHeader pageHeaderActions"><div><p className="eyebrow">Records Engine</p><h1>{table.technical_name||table.table_name}</h1><p>{table.fields?.length || 0} campos · PK {(pkColumns).join(", ") || "sin definir"}</p></div><div className="formActions"><Link className="button secondaryButton" href="/app/records">Volver</Link><button type="button" className="button secondaryButton" onClick={() => setShowFilters((value) => !value)}>Filtros</button>{canWrite && <button type="button" className="button primaryButton" onClick={() => { setEditing(null); setShowForm(true); }}>Nuevo registro</button>}</div></header>
    {error && <Alert type="error">{error}</Alert>}{message && <Alert type="success">{message}</Alert>}
    {!canWrite && <Alert type="info">Tu rol permite lectura, pero no crear, editar ni eliminar registros.</Alert>}
    {!simplePk && <Alert type="info">La tabla no tiene una PK simple. Puedes listar y crear filas, pero el backend no permite PATCH/DELETE por registro en esta fase.</Alert>}
    {showFilters && <section className="card"><RecordFilters fields={table.fields || []} filters={filters} setFilters={setFilters} onApply={() => { setAppliedFilters(filters); setOffset(0); loadRows(0, filters, orderBy, limit); }} onClear={() => { setFilters([]); setAppliedFilters([]); setOffset(0); loadRows(0, [], orderBy, limit); }} /></section>}
    {showForm && <section className="card"><div className="cardHeader"><div><h2>{editing ? "Editar registro" : "Nuevo registro"}</h2><p>{editing ? `Versión esperada: ${editing[versionColumn]}` : "El formulario se genera a partir de FieldAsset."}</p></div></div><RecordForm key={editing ? `${editing[pkField]}-${editing[versionColumn]}` : "new"} table={table} record={editing} onSubmit={save} onCancel={() => { setShowForm(false); setEditing(null); }} isSaving={isSaving} /></section>}
    <section className="card"><div className="cardHeader responsiveCardHeader"><div><h2>Registros</h2><p>{returned} fila(s) devueltas · offset {offset}</p></div><div className="paginationControls"><label>Filas<select value={limit} onChange={(e) => { const next = Number(e.target.value); setLimit(next); setOffset(0); loadRows(0, appliedFilters, orderBy, next); }}>{[10,25,50,100].map((value) => <option key={value}>{value}</option>)}</select></label><button type="button" className="button secondaryButton smallButton" disabled={offset === 0 || isLoading} onClick={() => loadRows(Math.max(0, offset - limit))}>Anterior</button><button type="button" className="button secondaryButton smallButton" disabled={returned < limit || isLoading} onClick={() => loadRows(offset + limit)}>Siguiente</button><button type="button" className="button secondaryButton smallButton" disabled={isLoading} onClick={() => loadRows()}>Recargar</button></div></div>
      {isLoading ? <Spinner label="Cargando registros..." /> : rows.length === 0 ? <EmptyState title="Sin registros" description="No hay filas para los filtros y página actuales." /> : <div className="tableWrap"><table className="dataTable recordTable"><thead><tr>{(table.fields || []).map((field) => <th key={field.id}><button type="button" className="sortButton" onClick={() => changeOrder(field.name)}>{field.name}{orderBy === field.name ? " ↑" : orderBy === `-${field.name}` ? " ↓" : ""}</button></th>)}<th>Versión</th>{canWrite && simplePk && <th>Acciones</th>}</tr></thead><tbody>{rows.map((row, index) => <tr key={`${simplePk ? row[pkField] : index}-${row[versionColumn]}`}>
        {(table.fields || []).map((field) => <td key={field.id} title={formatCell(row[field.name])}>{formatCell(row[field.name])}</td>)}<td><code>{row[versionColumn]}</code></td>{canWrite && simplePk && <td><div className="tableActions"><button type="button" className="button secondaryButton smallButton" onClick={() => { setEditing(row); setShowForm(true); }}>Editar</button><button type="button" className="button dangerButton smallButton" onClick={() => remove(row)}>Eliminar</button></div></td>}
      </tr>)}</tbody></table></div>}
    </section>
  </div>;
}
