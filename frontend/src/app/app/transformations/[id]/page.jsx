"use client";

import Link from "next/link";
import { use, useEffect, useMemo, useState } from "react";

import Alert from "@/components/ui/Alert";
import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";
import ExecutionStatus from "@/components/logic/ExecutionStatus";
import PrepareTabs from "@/components/prepare/PrepareTabs";
import { useWorkspace } from "@/lib/hooks/useWorkspace";
import { getExecution } from "@/lib/services/executions";
import { getTransformation, previewTransformation, runTransformation } from "@/lib/services/transformations";
import { getApiErrorMessage } from "@/lib/utils/errors";

const WRITE_ROLES = ["OWNER", "ADMIN", "BUILDER"];
const TERMINAL = new Set(["SUCCESS", "FAILED", "CANCELLED", "BLOCKED"]);

export default function TransformationDetailPage({ params }) {
  const { id } = use(params);
  const { activeWorkspace, organizations } = useWorkspace();
  const [item, setItem] = useState(null);
  const [preview, setPreview] = useState(null);
  const [execution, setExecution] = useState(null);
  const [limit, setLimit] = useState(100);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const organization = useMemo(() => organizations.find((org) => org.id === activeWorkspace?.organization), [organizations, activeWorkspace]);
  const canWrite = WRITE_ROLES.includes(organization?.current_user_role);

  async function load() {
    setLoading(true); setError("");
    try { setItem(await getTransformation(id)); }
    catch (requestError) { setError(getApiErrorMessage(requestError)); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, [id]);

  useEffect(() => {
    if (!execution?.id || TERMINAL.has(execution.status)) return;
    const timer = window.setInterval(async () => {
      try { setExecution(await getExecution(execution.id)); } catch {}
    }, 2000);
    return () => window.clearInterval(timer);
  }, [execution?.id, execution?.status]);

  async function doPreview() {
    setBusy(true); setError(""); setPreview(null);
    try { setPreview(await previewTransformation(id, Number(limit))); }
    catch (requestError) { setError(getApiErrorMessage(requestError)); }
    finally { setBusy(false); }
  }

  async function run() {
    setBusy(true); setError(""); setMessage("");
    try {
      const result = await runTransformation(id);
      setMessage("Ejecución enviada a la cola SQL.");
      setExecution(await getExecution(result.execution_id));
    } catch (requestError) { setError(getApiErrorMessage(requestError)); }
    finally { setBusy(false); }
  }

  if (loading) return <Spinner label="Cargando transformación..." />;
  if (!item) return <EmptyState title="Transformación no encontrada" description={error || "No se pudo cargar la definición."} />;

  return <div className="pageStack">
    <header className="pageHeader pageHeaderActions"><div><p className="eyebrow">Prepare · SQL</p><h1>{item.name}</h1><p>{item.description || "Sin descripción"}</p></div><div className="formActions"><Link className="button secondaryButton" href="/app/transformations">Volver</Link>{canWrite && <button type="button" className="button primaryButton" disabled={busy || !item.enabled} onClick={run}>Ejecutar</button>}</div></header>
    <PrepareTabs />{error && <Alert type="error">{error}</Alert>}{message && <Alert type="success">{message}</Alert>}
    <section className="prepareDetailFlow"><div><small>INPUT</small><strong>{item.inputs?.length || 0} asset(s)</strong></div><span>→</span><div><small>TRANSFORM</small><strong>SQL · SELECT/WITH</strong></div><span>→</span><div><small>OUTPUT</small><strong>{item.output_mode}</strong></div><span>→</span><div><small>STATUS</small><strong>{item.output_asset ? "READY" : "NOT MATERIALIZED"}</strong></div></section><div className="statGrid"><div className="statCard"><span>Output</span><strong>{item.output_mode}</strong></div><div className="statCard"><span>Refresh</span><strong>{item.refresh_policy}</strong></div><div className="statCard"><span>Inputs conocidos</span><strong>{item.inputs?.length || 0}</strong></div><div className="statCard"><span>Output Asset</span><strong>{item.output_asset ? "Generado" : "Pendiente"}</strong></div></div>
    <section className="card"><div className="cardHeader"><div><h2>SQL</h2><p>Los tokens son resueltos por el backend antes de ejecutar.</p></div></div><pre className="codeBlock">{item.sql}</pre>{item.inputs?.length > 0 && <div className="chipList">{item.inputs.map((input) => <span className="statusBadge" key={input.id}>{input.asset_name || input.asset}</span>)}</div>}</section>
    <section className="card"><div className="cardHeader"><div><h2>Preview</h2><p>Ejecuta el SELECT sin materializar el output.</p></div><div className="formActions"><select value={limit} onChange={(e) => setLimit(e.target.value)}><option value="25">25</option><option value="100">100</option><option value="250">250</option><option value="500">500</option></select><button type="button" className="button secondaryButton" disabled={busy} onClick={doPreview}>Previsualizar</button></div></div>{preview && <><p className="mutedText">{preview.returned} fila(s) · {preview.input_assets?.length || 0} input asset(s)</p><div className="tableWrap"><table className="dataTable"><thead><tr>{preview.columns?.map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>{preview.rows?.map((row, index) => <tr key={index}>{preview.columns.map((column) => <td key={column}>{formatCell(row[column])}</td>)}</tr>)}</tbody></table></div></>}</section>
    {execution && <section className="card"><div className="cardHeader"><div><h2>Última ejecución iniciada</h2><p>{execution.id}</p></div><ExecutionStatus status={execution.status} /></div><div className="progressTrack"><div className="progressFill" style={{ width: `${execution.progress || 0}%` }} /></div><p>{execution.progress || 0}% · Queue: {execution.queue}</p>{execution.error_message && <Alert type="error">{execution.error_message}</Alert>}</section>}
  </div>;
}

function formatCell(value) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
