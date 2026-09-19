"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import SourceSyncForm from "@/components/dataSources/SourceSyncForm";
import SourceLifecyclePanel from "@/components/dataSources/SourceLifecyclePanel";
import RuntimeCredentialsForm from "@/components/dataSources/RuntimeCredentialsForm";
import Alert from "@/components/ui/Alert";
import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";
import { useWorkspace } from "@/lib/hooks/useWorkspace";
import { listCatalogTables, syncCatalog } from "@/lib/services/dataModel";
import { getDataSource, readDataSourcePage, testDataSourceConnection } from "@/lib/services/dataSources";
import { listGatewayJobs, queueGatewayJob } from "@/lib/services/customerGateway";
import { createSyncPolicy, listSyncPolicies, runSyncPolicy } from "@/lib/services/importExport";
import { getApiErrorMessage } from "@/lib/utils/errors";

const WRITE_ROLES = ["OWNER", "ADMIN", "BUILDER"];
const asList = (value) => Array.isArray(value) ? value : value?.results || [];

function sanitizeRuntime(input) {
  const output = {};
  Object.entries(input || {}).forEach(([key, value]) => {
    if (value === "" || value === null || value === undefined) return;
    if (["port", "connect_timeout"].includes(key)) output[key] = Number(value);
    else output[key] = value;
  });
  return output;
}

function sleep(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }

export default function DataSourceDetailPage() {
  const params = useParams();
  const sourceId = params.id;
  const { organizations, workspaces } = useWorkspace();
  const [source, setSource] = useState(null);
  const [runtime, setRuntime] = useState({});
  const [tables, setTables] = useState([]);
  const [selectedTable, setSelectedTable] = useState(null);
  const [preview, setPreview] = useState(null);
  const [policies, setPolicies] = useState([]);
  const [syncTable, setSyncTable] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [busyAction, setBusyAction] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [result, setResult] = useState(null);

  useEffect(() => {
    (async () => {
      setIsLoading(true); setError("");
      try {
        const nextSource = await getDataSource(sourceId);
        setSource(nextSource);
        const [tableResponse, policyResponse] = await Promise.all([
          listCatalogTables(sourceId),
          listSyncPolicies(nextSource.workspace, sourceId),
        ]);
        const nextTables = asList(tableResponse);
        setTables(nextTables);
        setPolicies(asList(policyResponse));
        if (nextTables.length) setSelectedTable(nextTables[0]);
      } catch (requestError) { setError(getApiErrorMessage(requestError)); }
      finally { setIsLoading(false); }
    })();
  }, [sourceId]);

  const sourceWorkspace = useMemo(() => workspaces.find((item) => item.id === source?.workspace), [workspaces, source]);
  const organization = useMemo(() => organizations.find((item) => item.id === sourceWorkspace?.organization), [organizations, sourceWorkspace]);
  const canManage = WRITE_ROLES.includes(organization?.current_user_role);
  const isManaged = source?.mode === "MANAGED";
  const isExternal = source?.mode === "EXTERNAL";
  const isGateway = source?.mode === "PRIVATE_GATEWAY";
  const directConnectorSupported = source && ["POSTGRESQL", "SQLSERVER"].includes(source.engine) && isExternal;

  async function reloadMetadata() {
    const [tableResponse, policyResponse] = await Promise.all([
      listCatalogTables(source.id),
      listSyncPolicies(source.workspace, source.id),
    ]);
    const nextTables = asList(tableResponse);
    setTables(nextTables);
    setPolicies(asList(policyResponse));
    if (selectedTable) setSelectedTable(nextTables.find((item) => item.id === selectedTable.id) || nextTables[0] || null);
    else if (nextTables.length) setSelectedTable(nextTables[0]);
  }

  async function waitForGatewayJob(jobId, timeoutMs = 45000) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      const jobs = asList(await listGatewayJobs(source.id));
      const job = jobs.find((item) => item.id === jobId);
      if (job?.status === "SUCCESS") return job;
      if (["FAILED", "CANCELLED", "EXPIRED"].includes(job?.status)) throw new Error(job.error_message || `Gateway job ${job.status}`);
      await sleep(1200);
    }
    throw new Error("The Gateway did not complete the request in time. Verify that the agent is online.");
  }

  async function runTest() {
    setBusyAction("test"); setError(""); setResult(null); setMessage("");
    try {
      if (isGateway) {
        const queued = await queueGatewayJob(source.id, { operation: "TEST_CONNECTION", payload: {} });
        const completed = await waitForGatewayJob(queued.id);
        setResult(completed.result || { ok: true });
      } else if (directConnectorSupported) {
        setResult(await testDataSourceConnection(source.id, sanitizeRuntime(runtime)));
      }
    } catch (requestError) { setError(getApiErrorMessage(requestError)); }
    finally { setBusyAction(""); }
  }

  async function synchronizeCatalog() {
    setBusyAction("catalog"); setError(""); setMessage("");
    try {
      if (isGateway) {
        const queued = await queueGatewayJob(source.id, { operation: "CATALOG", payload: { include_views: true } });
        await waitForGatewayJob(queued.id, 90000);
      } else if (directConnectorSupported) {
        await syncCatalog(source.id, sanitizeRuntime(runtime));
      }
      await reloadMetadata();
      setMessage("Catalog synchronized. Table metadata is now available to Data Model and import workflows.");
    } catch (requestError) { setError(getApiErrorMessage(requestError)); }
    finally { setBusyAction(""); }
  }

  async function loadPreview(table = selectedTable, nextOffset = 0) {
    if (!table) return;
    setBusyAction("read"); setError(""); setMessage("");
    try {
      let data;
      if (isGateway) {
        const queued = await queueGatewayJob(source.id, { operation: "READ_PAGE", payload: { schema: table.schema_name, table: table.table_name, limit: 50, offset: nextOffset } });
        const completed = await waitForGatewayJob(queued.id);
        data = completed.result || {};
      } else {
        data = await readDataSourcePage(source.id, { ...sanitizeRuntime(runtime), schema: table.schema_name, table: table.table_name, limit: 50, offset: nextOffset });
      }
      setPreview({ ...data, offset: nextOffset });
      setSelectedTable(table);
    } catch (requestError) { setError(getApiErrorMessage(requestError)); }
    finally { setBusyAction(""); }
  }

  async function createImportPolicy(payload) {
    setBusyAction("sync-policy"); setError(""); setMessage("");
    try {
      const policy = await createSyncPolicy(payload);
      const execution = await runSyncPolicy(policy.id);
      setMessage(`Managed import created and first refresh queued. Execution ${execution.execution_id}.`);
      setSyncTable(null);
      await reloadMetadata();
    } catch (requestError) { setError(getApiErrorMessage(requestError)); }
    finally { setBusyAction(""); }
  }

  if (isLoading) return <Spinner label="Loading Data Source…" />;
  if (!source) return <EmptyState title="Data Source unavailable" description={error || "The requested source was not found."} />;

  return (
    <div className="pageStack dataSourceDetailPage">
      <header className="pageHeader pageHeaderActions">
        <div><p className="eyebrow">Data Source</p><h1>{source.name}</h1><p>{source.mode} · {source.engine} · {source.status}</p></div>
        <div className="tableActions"><Link href="/app/import-export" className="button secondaryButton">Import & refresh</Link><Link href="/app/data-sources" className="button secondaryButton">←</Link></div>
      </header>

      {error && <Alert type="error">{error}</Alert>}
      {message && <Alert type="success">{message}</Alert>}

      {!isManaged && <SourceLifecyclePanel source={source} canManage={canManage} managedCopies={policies.length} />}

      {isManaged ? <>
        <section className="card managedSourceHero">
          <div><span className="sourceModeMark">Managed / Platform</span><h2>Platform-managed storage</h2><p>Files and synchronized copies from external systems become physical Managed tables here. Host, port, database user and SSL are managed internally by the platform.</p></div>
          <Link className="button primaryButton" href="/app/import-export">Import CSV / Excel</Link>
        </section>
        <section className="card"><div className="cardHeader"><div><h2>Managed tables</h2><p>{tables.length} table(s) currently registered for this source.</p></div><Link href="/app/data-model" className="button secondaryButton">Open Data Model</Link></div>{tables.length ? <div className="tableWrap"><table className="dataTable"><thead><tr><th>Table</th><th>Fields</th><th>Type</th><th></th></tr></thead><tbody>{tables.map((table) => <tr key={table.id}><td><strong>{table.technical_name||table.table_name}</strong></td><td>{table.fields?.length || 0}</td><td>{table.object_type}</td><td><Link className="button smallButton secondaryButton" href={`/app/data-table?table=${table.id}`}>Open</Link></td></tr>)}</tbody></table></div> : <EmptyState title="No Managed tables yet" description="Import CSV/Excel, create a table in Data Model, or synchronize an External / Private Gateway table." actionHref="/app/import-export" actionLabel="Import data" />}</section>
      </> : <>
        <section className="card sourceAccessCard">
          <div className="cardHeader"><div><h2>Access path</h2><p>{isGateway ? "The platform reaches this database through the customer-side Gateway agent." : "The platform connects directly to the external database over the network."}</p></div></div>
          <div className="sourceAccessDiagram"><span>BI Platform</span><b>→</b>{isGateway && <><span>Private Gateway</span><b>→</b></>}<span>{source.engine}</span></div>
          <div className="sourceAccessOptions">
            <div className="sourceAccessOption"><strong>Direct / Live</strong><p>No Managed table is created. Preview requests read the source again, so source changes appear on the next query.</p></div>
            <div className="sourceAccessOption"><strong>Import to Managed</strong><p>Creates a separate Managed table. Changes in the source appear only when its refresh policy runs.</p></div>
          </div>
          {directConnectorSupported && canManage && <RuntimeCredentialsForm source={source} value={runtime} onChange={setRuntime} />}
          {isExternal && <p className="fieldHint">Scheduled refresh uses the encrypted credentials stored for this Data Source. Runtime credentials entered here are only used for the current request.</p>}
          <div className="formActions"><button type="button" className="button secondaryButton" onClick={runTest} disabled={busyAction === "test"}>{busyAction === "test" ? "Testing…" : "Test connection"}</button><button type="button" className="button primaryButton" onClick={synchronizeCatalog} disabled={busyAction === "catalog"}>{busyAction === "catalog" ? "Synchronizing…" : tables.length ? "Refresh catalog" : "Synchronize catalog"}</button></div>
          {result && <pre className="codePanel">{JSON.stringify(result, null, 2)}</pre>}
        </section>

        <section className="card">
          <div className="cardHeader responsiveCardHeader"><div><h2>Source tables</h2><p>Catalog metadata is stored in the platform. Direct preview reads rows from the source; Import creates a Managed copy.</p></div><span className="quotaHint">{tables.length} objects</span></div>
          {tables.length ? <div className="catalogLayout sourceTableCatalog"><div className="catalogList">{tables.map((table) => <button type="button" key={table.id} className={`catalogItem ${selectedTable?.id === table.id ? "selectedCatalogItem" : ""}`} onClick={() => { setSelectedTable(table); setPreview(null); }}><strong>{table.technical_name||table.table_name}</strong><span>{table.object_type} · {table.fields?.length || 0} fields</span></button>)}</div><div className="catalogDetail">{selectedTable ? <><div className="cardHeader responsiveCardHeader"><div><h3>{selectedTable.technical_name||selectedTable.table_name}</h3><p>Choose live access or create a Managed copy.</p></div><div className="tableActions"><button type="button" className="button smallButton secondaryButton" onClick={() => loadPreview(selectedTable, 0)} disabled={busyAction === "read"}>{busyAction === "read" ? "Reading…" : "Live preview"}</button>{canManage && <button type="button" className="button smallButton primaryButton" onClick={() => setSyncTable(selectedTable)}>Import to Managed</button>}</div></div><div className="tableWrap"><table className="dataTable"><thead><tr><th>Field</th><th>Type</th><th>Native</th><th>Nullable</th><th>PK</th></tr></thead><tbody>{selectedTable.fields?.map((field) => <tr key={field.id || field.name}><td><strong>{field.name}</strong></td><td>{field.logical_type}</td><td>{field.native_type}</td><td>{field.nullable ? "Yes" : "No"}</td><td>{field.is_primary_key ? "Yes" : "—"}</td></tr>)}</tbody></table></div></> : <EmptyState title="Select a table" description="Choose a catalog table to inspect it." />}</div></div> : <EmptyState title="Catalog not synchronized" description={isGateway ? "The Gateway must be online. Synchronize the catalog to discover private tables without exposing the database publicly." : "Test the connection and synchronize the catalog to discover schemas, tables and fields."} />}
        </section>

        {syncTable && <section className="card syncPolicyEditorCard"><div className="cardHeader"><div><h2>Import {syncTable.table_name}</h2><p>This creates a Platform Copy. Synchronization is managed automatically by the platform.</p></div></div><SourceSyncForm workspaceId={source.workspace} source={source} table={syncTable} onSubmit={createImportPolicy} onCancel={() => setSyncTable(null)} isSaving={busyAction === "sync-policy"} /></section>}

        {preview && <section className="card"><div className="cardHeader responsiveCardHeader"><div><h2>Live preview</h2><p>Fresh read from {selectedTable?.table_name}. Reload to see new source changes.</p></div><button type="button" className="button secondaryButton smallButton" onClick={() => loadPreview(selectedTable, preview.offset || 0)}>Refresh live data</button></div><div className="tableWrap">{preview.rows?.length ? <table className="dataTable"><thead><tr>{Object.keys(preview.rows[0]).map((key) => <th key={key}>{key}</th>)}</tr></thead><tbody>{preview.rows.map((row, index) => <tr key={index}>{Object.keys(preview.rows[0]).map((key) => <td key={key}>{row[key] === null ? <span className="mutedText">NULL</span> : typeof row[key] === "object" ? JSON.stringify(row[key]) : String(row[key])}</td>)}</tr>)}</tbody></table> : <EmptyState title="No rows" description="The source returned no records." />}</div></section>}

        <section className="card"><div className="cardHeader responsiveCardHeader"><div><h2>Managed refresh policies</h2><p>Imported copies are independent tables. These policies define when source changes are copied into Managed storage.</p></div><Link href="/app/import-export" className="button secondaryButton">All data movement</Link></div>{policies.length ? <div className="tableWrap"><table className="dataTable"><thead><tr><th>Source table</th><th>Managed target</th><th>Strategy</th><th>Refresh</th><th>Status</th><th>Last sync</th></tr></thead><tbody>{policies.map((policy) => <tr key={policy.id}><td>{policy.source_table_label}</td><td>{policy.target_table_label || policy.target_table_name}</td><td>{policy.strategy}{policy.incremental_field && <span className="tableSecondary">{policy.incremental_field}</span>}</td><td>{policy.schedule}</td><td><span className={`statusBadge status-${policy.status}`}>{policy.status}</span></td><td>{policy.last_sync_at ? new Date(policy.last_sync_at).toLocaleString() : "Never"}<span className="tableSecondary">{policy.last_rows || 0} rows</span></td></tr>)}</tbody></table></div> : <EmptyState title="No Managed copies" description="Choose Import to Managed on a source table when you want a platform-owned copy or scheduled refresh." />}</section>
      </>}
    </div>
  );
}
