"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import PythonTransformationForm from "@/components/dataScience/PythonTransformationForm";
import TransformationForm from "@/components/logic/TransformationForm";
import PrepareTabs from "@/components/prepare/PrepareTabs";
import Alert from "@/components/ui/Alert";
import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";
import { useWorkspace } from "@/lib/hooks/useWorkspace";
import { listDataAssets, listDataSources } from "@/lib/services/dataSources";
import {
  createPythonTransformation, deletePythonTransformation, listPythonTransformations, updatePythonTransformation,
} from "@/lib/services/dataScience";
import {
  createTransformation, deleteTransformation, listTransformations, updateTransformation,
} from "@/lib/services/transformations";
import { getApiErrorMessage } from "@/lib/utils/errors";

const WRITE_ROLES = ["OWNER", "ADMIN", "BUILDER"];
const listValue = (data) => Array.isArray(data) ? data : data?.results || [];

export default function TransformationsPage() {
  const { activeWorkspace, organizations } = useWorkspace();
  const [sqlItems, setSqlItems] = useState([]);
  const [pythonItems, setPythonItems] = useState([]);
  const [assets, setAssets] = useState([]);
  const [kind, setKind] = useState("ALL");
  const [query, setQuery] = useState("");
  const [formType, setFormType] = useState("");
  const [editing, setEditing] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const organization = useMemo(
    () => organizations.find((item) => item.id === activeWorkspace?.organization),
    [organizations, activeWorkspace],
  );
  const canWrite = WRITE_ROLES.includes(organization?.current_user_role);

  async function load() {
    if (!activeWorkspace?.id) { setLoading(false); return; }
    setLoading(true); setError("");
    try {
      const [sqlData, pythonData, assetData, sourceData] = await Promise.all([
        listTransformations(activeWorkspace.id),
        listPythonTransformations(activeWorkspace.id),
        listDataAssets(activeWorkspace.id),
        listDataSources(activeWorkspace.id),
      ]);
      const sources = listValue(sourceData);
      const managedIds = new Set(sources.filter((source) => source.mode === "MANAGED").map((source) => source.id));
      setSqlItems(listValue(sqlData));
      setPythonItems(listValue(pythonData));
      setAssets(listValue(assetData).filter((asset) =>
        managedIds.has(asset.data_source) && ["TABLE", "VIEW", "DERIVED_TABLE", "DATASET"].includes(asset.asset_type)
      ));
    } catch (requestError) { setError(getApiErrorMessage(requestError)); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, [activeWorkspace?.id]);

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    const sql = sqlItems.map((item) => ({ ...item, prepareKind: "SQL" }));
    const python = pythonItems.map((item) => ({ ...item, prepareKind: "PYTHON" }));
    return [...sql, ...python]
      .filter((item) => kind === "ALL" || item.prepareKind === kind)
      .filter((item) => !q || `${item.name} ${item.description || ""} ${item.output_name || ""}`.toLowerCase().includes(q));
  }, [sqlItems, pythonItems, kind, query]);

  function openForm(type, item = null) { setFormType(type); setEditing(item); setError(""); setMessage(""); }
  function closeForm() { setFormType(""); setEditing(null); }

  async function saveSql(payload) {
    setSaving(true); setError("");
    try {
      if (editing) await updateTransformation(editing.id, payload);
      else await createTransformation(payload);
      setMessage(editing ? "SQL transformation updated." : "SQL transformation created.");
      closeForm(); await load();
    } catch (e) { setError(getApiErrorMessage(e)); } finally { setSaving(false); }
  }

  async function savePython(payload) {
    setSaving(true); setError("");
    try {
      if (editing) await updatePythonTransformation(editing.id, payload);
      else await createPythonTransformation(payload);
      setMessage(editing ? "Python transformation updated." : "Python transformation created.");
      closeForm(); await load();
    } catch (e) { setError(getApiErrorMessage(e)); } finally { setSaving(false); }
  }

  async function remove(item) {
    if (!window.confirm(`Delete "${item.name}"?`)) return;
    try {
      if (item.prepareKind === "PYTHON") await deletePythonTransformation(item.id);
      else await deleteTransformation(item.id);
      setMessage("Transformation deleted."); await load();
    } catch (e) { setError(getApiErrorMessage(e)); }
  }

  if (!activeWorkspace) return <EmptyState title="Select a workspace" description="Prepare is scoped to the active workspace." />;

  return <div className="pageStack">
    <header className="pageHeader pageHeaderActions">
      <div><p className="eyebrow">Prepare</p><h1>Transformations</h1><p>Turn governed inputs into reusable outputs with SQL or Python, then follow execution and lineage from the same workflow.</p></div>
      {canWrite && <div className="headerActions">
        <button type="button" className="button secondaryButton" onClick={() => openForm("PYTHON")}>+ Python</button>
        <button type="button" className="button primaryButton" onClick={() => openForm("SQL")}>+ SQL transformation</button>
      </div>}
    </header>
    <PrepareTabs />
    {error && <Alert type="error">{error}</Alert>}
    {message && <Alert type="success">{message}</Alert>}

    <section className="prepareFlowHero">
      <div><span className="prepareFlowStep">1</span><strong>Input</strong><small>Choose governed data assets</small></div>
      <span className="prepareFlowArrow">→</span>
      <div><span className="prepareFlowStep">2</span><strong>Transform</strong><small>SQL or controlled Python</small></div>
      <span className="prepareFlowArrow">→</span>
      <div><span className="prepareFlowStep">3</span><strong>Output</strong><small>Materialize a reusable asset</small></div>
      <span className="prepareFlowArrow">→</span>
      <div><span className="prepareFlowStep">4</span><strong>Observe</strong><small>Activity and lineage</small></div>
    </section>

    {formType && <section className="card">
      <div className="cardHeader"><div>
        <p className="eyebrow">{formType}</p>
        <h2>{editing ? "Edit" : "New"} {formType === "SQL" ? "SQL transformation" : "Python transformation"}</h2>
        <p>{formType === "SQL" ? "SELECT/WITH only. Asset tokens keep physical names and credentials outside your SQL." : 'Use table("alias") and save_table(dataframe). The runtime is package- and resource-limited.'}</p>
      </div></div>
      {formType === "SQL"
        ? <TransformationForm workspaceId={activeWorkspace.id} initialValue={editing} assets={assets} onSubmit={saveSql} onCancel={closeForm} isSaving={saving} />
        : <PythonTransformationForm workspaceId={activeWorkspace.id} initialValue={editing} onSubmit={savePython} onCancel={closeForm} isSaving={saving} />}
    </section>}

    <section className="card prepareLibrary">
      <div className="prepareToolbar">
        <div><h2>Transformation library</h2><p>{sqlItems.length} SQL · {pythonItems.length} Python</p></div>
        <div className="prepareToolbarControls">
          <input aria-label="Search transformations" placeholder="Search transformations..." value={query} onChange={(e) => setQuery(e.target.value)} />
          <select aria-label="Transformation type" value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="ALL">All types</option><option value="SQL">SQL</option><option value="PYTHON">Python</option>
          </select>
        </div>
      </div>
      {loading ? <Spinner label="Loading transformations..." /> : rows.length === 0
        ? <EmptyState title="No transformations found" description={query || kind !== "ALL" ? "Change your search or filter." : "Create a SQL or Python transformation to begin preparing data."} />
        : <div className="prepareCards">{rows.map((item) => {
          const python = item.prepareKind === "PYTHON";
          const href = python ? `/app/data-science/python/${item.id}` : `/app/transformations/${item.id}`;
          return <article className="prepareCard" key={`${item.prepareKind}-${item.id}`}>
            <div className="prepareCardTop"><span className={`prepareKind ${python ? "python" : "sql"}`}>{item.prepareKind}</span><span className={`statusBadge ${item.enabled ? "status-success" : "status-blocked"}`}>{item.enabled ? "ENABLED" : "DISABLED"}</span></div>
            <div><h3>{item.name}</h3><p>{item.description || "No description"}</p></div>
            <div className="preparePipeline">
              <div><small>INPUTS</small><strong>{item.inputs?.length || 0}</strong></div><span>→</span>
              <div><small>OUTPUT</small><strong>{python ? item.output_name : item.output_mode}</strong></div><span>→</span>
              <div><small>ASSET</small><strong>{item.output_asset ? "READY" : "PENDING"}</strong></div>
            </div>
            <div className="prepareCardMeta">{python
              ? <><span>{item.timeout_seconds}s timeout</span><span>{item.memory_limit_mb} MB</span></>
              : <><span>{item.refresh_policy}</span><span>SELECT/WITH</span></>}
            </div>
            <div className="tableActions"><Link className="button secondaryButton smallButton" href={href}>Open</Link>{canWrite && <>
              <button type="button" className="button secondaryButton smallButton" onClick={() => openForm(item.prepareKind, item)}>Edit</button>
              <button type="button" className="button dangerButton smallButton" onClick={() => remove(item)}>Delete</button>
            </>}</div>
          </article>;
        })}</div>}
    </section>
  </div>;
}
