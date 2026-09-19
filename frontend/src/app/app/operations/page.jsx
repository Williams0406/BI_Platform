"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import HealthCard from "@/components/operations/HealthCard";
import ManageTabs from "@/components/manage/ManageTabs";
import Alert from "@/components/ui/Alert";
import { useWorkspace } from "@/lib/hooks/useWorkspace";
import { getLiveness, getReadiness } from "@/lib/services/health";
import { getOperationalStatus } from "@/lib/services/operations";
import { validateWorkspaceIntegration } from "@/lib/services/platformIntegration";
import { getApiErrorMessage } from "@/lib/utils/errors";

const EXECUTION_ORDER = ["QUEUED", "RUNNING", "SUCCESS", "FAILED", "CANCELLED", "BLOCKED"];

function readinessFromError(error) {
  return error?.response?.data || null;
}

function storageDetail(storage) {
  if (!storage) return "Sin datos";
  if (storage.ok) return storage.backend ? `Backend ${storage.backend}` : "Disponible";
  return storage.detail || "No disponible";
}

export default function OperationsPage() {
  const { activeWorkspace, activeWorkspaceId } = useWorkspace();
  const [loading, setLoading] = useState(true);
  const [live, setLive] = useState(null);
  const [ready, setReady] = useState(null);
  const [status, setStatus] = useState(null);
  const [statusForbidden, setStatusForbidden] = useState(false);
  const [checks, setChecks] = useState([]);
  const [error, setError] = useState("");
  const [lastCheckedAt, setLastCheckedAt] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    setStatusForbidden(false);

    const livePromise = getLiveness();
    const readyPromise = getReadiness().catch((requestError) => {
      const payload = readinessFromError(requestError);
      if (payload) return payload;
      throw requestError;
    });
    const statusPromise = getOperationalStatus().catch((requestError) => {
      if (requestError?.response?.status === 403) {
        setStatusForbidden(true);
        return null;
      }
      throw requestError;
    });
    const integrationPromise = activeWorkspaceId
      ? validateWorkspaceIntegration(activeWorkspaceId)
      : Promise.resolve([]);

    const results = await Promise.allSettled([
      livePromise,
      readyPromise,
      statusPromise,
      integrationPromise,
    ]);

    if (results[0].status === "fulfilled") setLive(results[0].value);
    else setLive(null);

    if (results[1].status === "fulfilled") setReady(results[1].value);
    else setReady(null);

    if (results[2].status === "fulfilled") setStatus(results[2].value);
    else setStatus(null);

    if (results[3].status === "fulfilled") setChecks(results[3].value);
    else setChecks([]);

    const firstFailure = results.find((item) => item.status === "rejected");
    if (firstFailure) setError(getApiErrorMessage(firstFailure.reason));

    setLastCheckedAt(new Date());
    setLoading(false);
  }, [activeWorkspaceId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    const timer = window.setInterval(refresh, 30000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const readinessOk = ready?.status === "ok";
  const integrationOk = checks.filter((item) => item.ok).length;
  const integrationFailed = checks.filter((item) => !item.ok).length;

  const executionTotal = useMemo(
    () => Object.values(status?.executions || {}).reduce((sum, value) => sum + Number(value || 0), 0),
    [status],
  );

  return (
    <div className="pageStack">
      <section className="pageHeader">
        <div>
          <p className="eyebrow">Manage · Platform health</p>
          <h1>Platform health</h1>
          <p>
            Check API health, required infrastructure, workspace integration and privileged platform telemetry.
          </p>
        </div>
        <div className="headerActions">
          <button type="button" className="button buttonSecondary" onClick={refresh} disabled={loading}>
            {loading ? "Validando..." : "Actualizar"}
          </button>
        </div>
      </section>

      <ManageTabs />

      {error ? <Alert>{error}</Alert> : null}

      <section className="opsHealthGrid">
        <HealthCard title="API · Liveness" ok={live?.status === "ok"} pending={loading && !live} detail="GET /api/v1/health/live/" />
        <HealthCard
          title="API · Readiness"
          ok={readinessOk}
          pending={loading && !ready}
          detail={readinessOk ? "Dependencias requeridas disponibles" : "Revisa los checks de readiness"}
        />
        <HealthCard
          title="Workspace Integration"
          ok={!activeWorkspaceId || integrationFailed === 0}
          pending={loading && activeWorkspaceId && checks.length === 0}
          detail={activeWorkspaceId ? `${integrationOk}/${checks.length || 17} módulos accesibles` : "Selecciona un workspace"}
        />
        <HealthCard
          title="Ops Telemetry"
          ok={Boolean(status)}
          pending={loading && !status && !statusForbidden}
          detail={statusForbidden ? "Requiere Django is_staff=True" : status ? "Telemetría privilegiada disponible" : "Sin telemetría"}
        />
      </section>

      <section className="card">
        <div className="cardHeader">
          <div>
            <p className="eyebrow">Readiness</p>
            <h2>Required services</h2>
          </div>
          {lastCheckedAt ? <small>Última comprobación: {lastCheckedAt.toLocaleTimeString()}</small> : null}
        </div>
        <div className="opsCheckGrid">
          {Object.entries(ready?.checks || {}).map(([name, value]) => {
            const ok = typeof value === "string" ? value === "available" : Boolean(value?.ok);
            return (
              <div className="opsCheckRow" key={name}>
                <span className={`opsStatusPill ${ok ? "ok" : "error"}`}>{ok ? "OK" : "ERROR"}</span>
                <strong>{name}</strong>
                <code>{typeof value === "string" ? value : JSON.stringify(value)}</code>
              </div>
            );
          })}
          {!ready?.checks ? <p className="muted">No hay información de readiness disponible.</p> : null}
        </div>
      </section>

      <section className="card">
        <div className="cardHeader">
          <div>
            <p className="eyebrow">Workspace integration</p>
            <h2>{activeWorkspace?.name || "Workspace no seleccionado"}</h2>
            <p className="muted">
              Verifica que los endpoints principales de cada engine sean accesibles con el usuario y workspace actuales. Un contador en cero significa que el módulo funciona pero todavía no tiene objetos configurados.
            </p>
          </div>
        </div>

        {!activeWorkspaceId ? <Alert type="info">Selecciona un workspace desde la barra superior.</Alert> : null}

        {activeWorkspaceId ? (
          <div className="opsModuleGrid">
            {checks.map((check) => (
              <Link className={`opsModuleCard ${check.ok ? "ok" : "error"}`} href={check.href} key={check.name}>
                <div>
                  <span className={`opsStatusPill ${check.ok ? "ok" : "error"}`}>{check.ok ? "OK" : "ERROR"}</span>
                  <strong>{check.name}</strong>
                </div>
                <b>{check.ok ? check.count : "—"}</b>
                <small>{check.detail}</small>
              </Link>
            ))}
          </div>
        ) : null}
      </section>

      <section className="card">
        <div className="cardHeader">
          <div>
            <p className="eyebrow">Platform telemetry</p>
            <h2>Infrastructure & runtime</h2>
          </div>
        </div>

        {statusForbidden ? (
          <Alert type="info">
            `/api/v1/ops/status/` is protected by Django `IsAdminUser`. Platform telemetry requires `is_staff=True`; workspace OWNER/ADMIN is a separate authorization boundary.
          </Alert>
        ) : null}

        {status ? (
          <>
            <div className="statGrid">
              <article className="statCard">
                <span>Database</span>
                <strong>{status.database?.vendor || "—"}</strong>
                <small>{status.database?.connections !== undefined ? `${status.database.connections} conexión(es)` : "Conectada"}</small>
              </article>
              <article className="statCard">
                <span>Redis / Cache</span>
                <strong>{status.redis?.ok ? "Disponible" : "Error"}</strong>
                <small>{status.redis?.detail || "Cache roundtrip"}</small>
              </article>
              <article className="statCard">
                <span>Artifact Storage</span>
                <strong>{status.artifact_backend || "—"}</strong>
                <small>{storageDetail(status.storage)}</small>
              </article>
              <article className="statCard">
                <span>Executions</span>
                <strong>{executionTotal}</strong>
                <small>Jobs registrados globalmente</small>
              </article>
              <article className="statCard">
                <span>Gateways</span>
                <strong>{status.gateways?.total ?? 0}</strong>
                <small>{status.gateways?.seen_last_5m ?? 0} vistos en últimos 5 min</small>
              </article>
              <article className="statCard">
                <span>Gateways revoked</span>
                <strong>{status.gateways?.revoked ?? 0}</strong>
                <small>Registros revocados</small>
              </article>
            </div>

            <div className="opsExecutionGrid">
              {EXECUTION_ORDER.map((name) => (
                <div key={name}>
                  <span>{name}</span>
                  <strong>{status.executions?.[name] || 0}</strong>
                </div>
              ))}
            </div>
          </>
        ) : !statusForbidden ? <p className="muted">No se pudo recuperar telemetría operacional.</p> : null}
      </section>

      <section className="card">
        <div className="cardHeader">
          <div>
            <p className="eyebrow">Product integration</p>
            <h2>End-to-end capability chain</h2>
          </div>
        </div>
        <div className="opsFlow">
          {["Data Sources", "Data Model", "Records", "Views", "Transformations", "Dependencies", "Metrics", "Analytics", "Data Science", "Optimization", "Import/Export", "Governance / Gateway"].map((item, index, array) => (
            <div className="opsFlowStep" key={item}>
              <span>{index + 1}</span>
              <strong>{item}</strong>
              {index < array.length - 1 ? <b>→</b> : null}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
