"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";

import Alert from "@/components/ui/Alert";
import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";
import ExecutionStatus from "@/components/logic/ExecutionStatus";
import { cancelExecution, getExecution } from "@/lib/services/executions";
import { getApiErrorMessage } from "@/lib/utils/errors";

const TERMINAL = new Set(["SUCCESS", "FAILED", "CANCELLED", "BLOCKED"]);

export default function ExecutionDetailPage({ params }) {
  const { id } = use(params);
  const [item, setItem] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load(silent = false) {
    if (!silent) setLoading(true);
    try { setItem(await getExecution(id)); setError(""); }
    catch (requestError) { setError(getApiErrorMessage(requestError)); }
    finally { if (!silent) setLoading(false); }
  }
  useEffect(() => { load(); }, [id]);
  useEffect(() => {
    if (!item || TERMINAL.has(item.status)) return;
    const timer = window.setInterval(() => load(true), 2000);
    return () => window.clearInterval(timer);
  }, [item?.status]);

  async function cancel() {
    try { await cancelExecution(id); await load(true); }
    catch (requestError) { setError(getApiErrorMessage(requestError)); }
  }

  if (loading) return <Spinner label="Cargando ejecución..." />;
  if (!item) return <EmptyState title="Ejecución no encontrada" description={error} />;

  return <div className="pageStack">
    <header className="pageHeader pageHeaderActions"><div><p className="eyebrow">Execution</p><h1>{item.object_type}</h1><p>{item.id}</p></div><div className="formActions"><Link className="button secondaryButton" href="/app/executions">Volver</Link>{["QUEUED", "RUNNING"].includes(item.status) && <button type="button" className="button dangerButton" onClick={cancel}>Cancelar ejecución</button>}</div></header>
    {error && <Alert type="error">{error}</Alert>}
    <div className="statGrid"><div className="statCard"><span>Status</span><ExecutionStatus status={item.status} /></div><div className="statCard"><span>Queue</span><strong>{item.queue}</strong></div><div className="statCard"><span>Progreso</span><strong>{item.progress || 0}%</strong></div><div className="statCard"><span>Duración</span><strong>{item.duration_ms == null ? "—" : `${item.duration_ms} ms`}</strong></div></div>
    <section className="card"><div className="progressTrack"><div className="progressFill" style={{ width: `${item.progress || 0}%` }} /></div><div className="detailGrid"><div><span>Queued</span><strong>{dateTime(item.queued_at)}</strong></div><div><span>Started</span><strong>{dateTime(item.started_at)}</strong></div><div><span>Finished</span><strong>{dateTime(item.finished_at)}</strong></div><div><span>Celery Task</span><strong>{item.celery_task_id || "—"}</strong></div></div></section>
    {item.error_message && <Alert type="error"><strong>{item.error_type || "ExecutionError"}</strong>: {item.error_message}</Alert>}
    <section className="card"><div className="cardHeader"><div><h2>Logs</h2><p>{item.logs?.length || 0} entrada(s)</p></div></div>{item.logs?.length ? <div className="logList">{item.logs.map((log) => <div className={`logEntry log-${log.level.toLowerCase()}`} key={log.id}><span>{dateTime(log.created_at)}</span><strong>{log.level}</strong><p>{log.message}</p>{Object.keys(log.metadata || {}).length > 0 && <pre>{JSON.stringify(log.metadata, null, 2)}</pre>}</div>)}</div> : <p className="mutedText">Sin logs todavía.</p>}</section>
    <div className="twoPanelGrid"><section className="card"><h2>Parameters</h2><pre className="codeBlock">{JSON.stringify(item.parameters || {}, null, 2)}</pre></section><section className="card"><h2>Result</h2><pre className="codeBlock">{JSON.stringify(item.result || {}, null, 2)}</pre></section></div>
  </div>;
}

function dateTime(value) { return value ? new Date(value).toLocaleString() : "—"; }
