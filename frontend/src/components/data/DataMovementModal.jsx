"use client";

import { useEffect, useMemo, useState } from "react";

import Alert from "@/components/ui/Alert";
import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";
import ImportJobForm from "@/components/platform/ImportJobForm";
import ExportJobForm from "@/components/platform/ExportJobForm";
import { useWorkspace } from "@/lib/hooks/useWorkspace";
import { listCatalogTables } from "@/lib/services/dataModel";
import { listDataSources } from "@/lib/services/dataSources";
import {
  createExport,
  createImport,
  downloadExport,
  getExport,
  previewImport,
  runImport,
} from "@/lib/services/importExport";
import { getQuota } from "@/lib/services/governance";
import { getApiErrorMessage } from "@/lib/utils/errors";

const WRITE = ["OWNER", "ADMIN", "BUILDER"];
const asList = (value) => Array.isArray(value) ? value : value?.results || [];

export default function DataMovementModal({onClose}) {
  const { activeWorkspace, organizations } = useWorkspace();
  const [tab, setTab] = useState("imports");
  const [tables, setTables] = useState([]);
  const [quota, setQuota] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [currentExport, setCurrentExport] = useState(null);
  const org = useMemo(() => organizations.find((item) => item.id === activeWorkspace?.organization), [organizations, activeWorkspace]);
  const canWrite = WRITE.includes(org?.current_user_role);

  async function load() {
    if (!activeWorkspace?.id) { setLoading(false); return; }
    setLoading(true); setError("");
    try {
      const [sourcesResponse, quotaResponse] = await Promise.all([
        listDataSources(activeWorkspace.id),
        getQuota(activeWorkspace.id),
      ]);
      const managedSources = asList(sourcesResponse).filter((source) => source.mode === "MANAGED");
      const tableChunks = await Promise.all(managedSources.map((source) => listCatalogTables(source.id)));
      setTables(tableChunks.flatMap(asList).filter((table) => table.object_type === "TABLE"));
      setQuota(quotaResponse);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [activeWorkspace?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  async function addImport(formData) {
    setSaving(true); setError(""); setMessage("");
    try {
      const job = await createImport(formData);
      setMessage("File uploaded. Review the preview before running the import.");
      const nextPreview = await previewImport(job.id);
      setPreview({ job, ...nextPreview });
      await load();
    } catch (requestError) { setError(getApiErrorMessage(requestError)); }
    finally { setSaving(false); }
  }

  async function addExport(payload) {
    setSaving(true); setError("");
    try { const job = await createExport(payload); setCurrentExport(job); setMessage("Export is being prepared."); }
    catch (requestError) { setError(getApiErrorMessage(requestError)); }
    finally { setSaving(false); }
  }

  useEffect(() => {
    if (!currentExport?.id || ["SUCCESS", "FAILED"].includes(currentExport.status)) return;
    const timer = setInterval(async () => {
      try { setCurrentExport(await getExport(currentExport.id)); } catch {}
    }, 2000);
    return () => clearInterval(timer);
  }, [currentExport?.id, currentExport?.status]);

  async function downloadCurrentExport() {
    if (!currentExport?.id) return;
    try {
      const blob = await downloadExport(currentExport.id);
      const url = URL.createObjectURL(blob); const a = document.createElement("a");
      a.href = url; a.download = `export_${currentExport.id}.${currentExport.file_type.toLowerCase()}`; a.click(); URL.revokeObjectURL(url);
    } catch (requestError) { setError(getApiErrorMessage(requestError)); }
  }

  async function executeJob(id) {
    try { const result = await runImport(id); setMessage(`Import queued. Execution ${result.execution_id}`); setPreview(null); await load(); }
    catch (requestError) { setError(getApiErrorMessage(requestError)); }
  }

  if (!activeWorkspace) return <EmptyState title="Select a workspace" description="Data movement works inside the active workspace." />;
  if (loading) return <Spinner label="Loading data movement…" />;

  return (
    <div className="dataMovementModalBody">
      <header className="packageExplorerHeader"><h2>Import / Export</h2><button className="packageRemove" onClick={onClose}>×</button></header>

      {error && <Alert type="error">{error}</Alert>}
      {message && <Alert type="success">{message}</Alert>}

      <div className="tabBar dataMovementTabs">
        <button type="button" className={tab === "imports" ? "active" : ""} onClick={() => setTab("imports")}>Files</button>
        <button type="button" className={tab === "exports" ? "active" : ""} onClick={() => setTab("exports")}>Export</button>
      </div>

      {tab === "imports" && <>
        <section className="card dataMovementPrimaryCard">
          <div className="cardHeader"><div><h2>Import a file</h2><p>A new file can create a physical table in Managed / Platform storage or update an existing Managed table.</p></div><span className="quotaHint">Up to {quota?.max_import_rows ?? "—"} rows / job</span></div>
          {canWrite ? <ImportJobForm workspaceId={activeWorkspace.id} tables={tables} onSubmit={addImport} isSaving={saving} /> : <Alert type="info">Your role is read-only.</Alert>}
        </section>

        {preview && <section className="card importPreviewCard">
          <div className="cardHeader responsiveCardHeader"><div><h2>Preview before import</h2><p>{preview.job.file_type}{preview.selected_sheet ? ` · ${preview.selected_sheet}` : ""} · {preview.rows?.length || 0} preview rows</p></div><button type="button" className="button primaryButton" onClick={() => executeJob(preview.job.id)}>Run import</button></div>
          {preview.sheets?.length > 1 && <Alert type="info">Workbook sheets detected: {preview.sheets.join(", ")}. The selected sheet is imported as the current table. Choose another sheet before uploading when you need a different worksheet.</Alert>}
          <div className="importSchemaGrid">{preview.inferred_schema?.map((field) => <div key={field.name} className="importSchemaField"><strong>{field.name}</strong><span>{field.logical_type}</span><small>from {field.source_name}</small></div>)}</div>
          <div className="tableWrap">{preview.rows?.length ? <table className="dataTable"><thead><tr>{Object.keys(preview.rows[0]).map((key) => <th key={key}>{key}</th>)}</tr></thead><tbody>{preview.rows.slice(0, 20).map((row, index) => <tr key={index}>{Object.keys(preview.rows[0]).map((key) => <td key={key}>{row[key] == null ? "NULL" : String(row[key])}</td>)}</tr>)}</tbody></table> : <EmptyState title="No rows detected" description="Check the selected sheet or file contents." />}</div>
        </section>}

      </>}

      {tab === "exports" && <><section className="card"><div className="cardHeader"><div><h2>Export Platform data</h2></div><span className="quotaHint">Up to {quota?.max_export_rows ?? "—"} rows / job</span></div>{canWrite ? <ExportJobForm workspaceId={activeWorkspace.id} tables={tables} onSubmit={addExport} isSaving={saving} maxRows={quota?.max_export_rows} /> : <Alert type="info">Your role is read-only.</Alert>}</section>{currentExport && <section className="card"><div className="cardHeader"><div><h2>Current export</h2><p>{currentExport.file_type} · {currentExport.status}{currentExport.rows_exported ? ` · ${currentExport.rows_exported} rows` : ""}</p></div>{currentExport.status === "SUCCESS" && <button className="button primaryButton" onClick={downloadCurrentExport}>Download</button>}</div>{currentExport.status === "FAILED" && <Alert type="error">{currentExport.error_message || "Export failed."}</Alert>}</section>}</>}

    </div>
  );
}
