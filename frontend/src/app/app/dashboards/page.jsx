"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import DashboardBuilder from "@/components/analytics/DashboardBuilder";
import ReportForm from "@/components/analytics/ReportForm";
import Alert from "@/components/ui/Alert";
import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";
import Icon from "@/components/ui/Icon";
import { useWorkspace } from "@/lib/hooks/useWorkspace";
import {
  createDashboard,
  createReport,
  deleteDashboard,
  deleteReport,
  listDashboards,
  listReports,
} from "@/lib/services/analytics";
import { deleteSemanticModel } from "@/lib/services/metrics";
import { getApiErrorMessage } from "@/lib/utils/errors";

function listValue(value) {
  return Array.isArray(value) ? value : value?.results || [];
}

const WRITE = ["OWNER", "ADMIN", "BUILDER"];
const isDraft = (dashboard) => dashboard?.layout?.workspace_state === "DRAFT";

export default function DashboardStudioPage() {
  const search = useSearchParams();
  const mode = search.get("mode") || "build";
  const { activeWorkspace, organizations } = useWorkspace();
  const [dashboards, setDashboards] = useState([]);
  const [reports, setReports] = useState([]);
  const [draftId, setDraftId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [createRep, setCreateRep] = useState(false);
  const [saving, setSaving] = useState(false);
  const loadKeyRef = useRef("");

  const org = useMemo(
    () => organizations.find((item) => item.id === activeWorkspace?.organization),
    [organizations, activeWorkspace]
  );
  const canWrite = WRITE.includes(org?.current_user_role);
  const publishedDashboards = useMemo(() => dashboards.filter((item) => !isDraft(item)), [dashboards]);

  async function load() {
    if (!activeWorkspace?.id) return;
    setLoading(true);
    setError("");
    try {
      const [dashboardResponse, reportResponse] = await Promise.all([
        listDashboards(activeWorkspace.id),
        listReports(activeWorkspace.id),
      ]);
      const dashboardList = listValue(dashboardResponse);
      setDashboards(dashboardList);
      setReports(listValue(reportResponse));

      const drafts = dashboardList.filter(isDraft);
      if (mode === "build" && canWrite) {
        // A draft is intentionally ephemeral. Reloading or reopening Canvas starts clean.
        for (const stale of drafts) {
          const autoModels = stale.layout?.auto_semantic_models || [];
          for (const binding of autoModels) {
            if (binding?.model_id) {
              try { await deleteSemanticModel(binding.model_id); } catch {}
            }
          }
          try { await deleteDashboard(stale.id); } catch {}
        }
        const draft = await createDashboard({
          workspace: activeWorkspace.id,
          name: "Untitled dashboard",
          description: "",
          layout: {
            grid: { columns: 12 },
            workspace_state: "DRAFT",
            auto_semantic_models: [],
            canvas: { kind: "DASHBOARD", preset: "16:9", width: 1280, height: 720, background: "#ffffff" },
          },
          global_filters: [],
        });
        setDashboards([...dashboardList.filter((item) => !isDraft(item)), draft]);
        setDraftId(draft.id);
      } else if (drafts.length) {
        // Leaving the unsaved canvas discards its automatically-created semantic models.
        for (const stale of drafts) {
          const autoModels = stale.layout?.auto_semantic_models || [];
          for (const binding of autoModels) {
            if (binding?.model_id) {
              try { await deleteSemanticModel(binding.model_id); } catch {}
            }
          }
          try { await deleteDashboard(stale.id); } catch {}
        }
        setDashboards(dashboardList.filter((item) => !isDraft(item)));
      }
    } catch (e) {
      setError(getApiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const key = `${activeWorkspace?.id || ""}:${mode}:${canWrite ? "write" : "read"}`;
    if (loadKeyRef.current === key) return;
    loadKeyRef.current = key;
    load();
  }, [activeWorkspace?.id, mode, canWrite]);

  async function addReport(payload) {
    setSaving(true);
    try {
      await createReport(payload);
      setCreateRep(false);
      await load();
    } catch (e) {
      setError(getApiErrorMessage(e));
    } finally {
      setSaving(false);
    }
  }

  async function remove(kind, item) {
    if (!window.confirm(`Delete ${item.name}?`)) return;
    try {
      if (kind === "dashboard") await deleteDashboard(item.id);
      else await deleteReport(item.id);
      await load();
    } catch (e) {
      setError(getApiErrorMessage(e));
    }
  }

  async function handlePublished() {
    if (draftId) window.location.href = `/app/dashboards/${draftId}`;
  }

  if (!activeWorkspace) {
    return <EmptyState title="Select a workspace" description="Dashboards belong to a workspace." />;
  }

  return (
    <div className="dashboardStudioPage dashboardAuthoringHome">
      <nav className="dashboardModeTabs compactDashboardModes" aria-label="Dashboard workspace modes">
        <Link className={mode === "build" ? "active" : ""} href="/app/dashboards">Canvas</Link>
        <Link className={mode === "library" ? "active" : ""} href="/app/dashboards?mode=library">Dashboards</Link>
        <Link className={mode === "reports" ? "active" : ""} href="/app/dashboards?mode=reports">Reports</Link>
      </nav>

      {error && <Alert type="error">{error}</Alert>}

      {mode === "build" && (
        loading && !draftId ? (
          <Spinner label="Opening canvas..." />
        ) : canWrite && draftId ? (
          <DashboardBuilder
            dashboardId={draftId}
            workspaceId={activeWorkspace.id}
            canWrite={canWrite}
            draftMode
            onPublished={handlePublished}
          />
        ) : (
          <EmptyState title="View-only workspace" description="A Builder, Admin or Owner can create dashboards here." />
        )
      )}

      {mode === "library" && (
        <section className="studioLibrary">
          {loading ? (
            <Spinner label="Loading dashboards..." />
          ) : publishedDashboards.length ? (
            <div className="overviewModuleGrid">
              {publishedDashboards.map((dashboard) => (
                <article className="overviewModule" key={dashboard.id}>
                  <Link href={`/app/dashboards/${dashboard.id}`} className="overviewModulePreview">
                    <Icon name="dashboard" size={34} />
                    <span>{dashboard.items?.length || 0} visuals</span>
                  </Link>
                  <div className="overviewModuleBody">
                    <div><strong>{dashboard.name}</strong><p>{dashboard.description || "Interactive decision view"}</p></div>
                    <div className="inlineActions">
                      <Link href={`/app/dashboards/${dashboard.id}`}>Edit</Link>
                      <Link href={`/app/dashboards/${dashboard.id}?fullscreen=1`}>View</Link>
                      {canWrite && <button type="button" onClick={() => remove("dashboard", dashboard)}>Delete</button>}
                    </div>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState title="No dashboards yet" description="Build on the Canvas and press Save when you want it to appear here and in Overview." />
          )}
        </section>
      )}

      {mode === "reports" && (
        <section className="studioLibrary">
          <div className="sectionHeading">
            <div />
            {canWrite && <button type="button" className="button primaryButton" onClick={() => setCreateRep(true)}>+ New report</button>}
          </div>
          {loading ? (
            <Spinner label="Loading reports..." />
          ) : reports.length ? (
            <div className="overviewModuleGrid">
              {reports.map((report) => (
                <article className="overviewModule" key={report.id}>
                  <Link href={`/app/reports/${report.id}?fullscreen=1`} className="overviewModulePreview">
                    <Icon name="report" size={34} />
                    <span>{report.default_export_format}</span>
                  </Link>
                  <div className="overviewModuleBody">
                    <div><strong>{report.name}</strong><p>{report.description || "Structured business report"}</p></div>
                    <div className="inlineActions">
                      <Link href={`/app/reports/${report.id}`}>Open</Link>
                      <Link href={`/app/reports/${report.id}?fullscreen=1`}>Full screen</Link>
                      {canWrite && <button type="button" onClick={() => remove("report", report)}>Delete</button>}
                    </div>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState title="No reports yet" description="Create a report when you need a structured output." />
          )}
        </section>
      )}

      {createRep && (
        <div className="modalBackdrop">
          <section className="semanticModal">
            <div className="cardHeader"><h2>New report</h2><button type="button" className="iconButton" onClick={() => setCreateRep(false)}>×</button></div>
            <ReportForm workspaceId={activeWorkspace.id} dashboards={publishedDashboards} onSubmit={addReport} onCancel={() => setCreateRep(false)} isSaving={saving} />
          </section>
        </div>
      )}
    </div>
  );
}
