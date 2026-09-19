"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import AnalyticsFilterBuilder, { normalizeAnalyticsFilters } from "@/components/analytics/AnalyticsFilterBuilder";
import ChartRenderer from "@/components/analytics/ChartRenderer";
import Alert from "@/components/ui/Alert";
import EmptyState from "@/components/ui/EmptyState";
import Icon from "@/components/ui/Icon";
import Spinner from "@/components/ui/Spinner";
import WorkspaceCommandBar from "@/components/data/WorkspaceCommandBar";
import ScriptWorkbench from "@/components/data/ScriptWorkbench";
import { useWorkspace } from "@/lib/hooks/useWorkspace";
import { createChart, getChart, listCharts, updateChart } from "@/lib/services/analytics";
import { getCatalogTable } from "@/lib/services/dataModel";
import { listSemanticModels, queryMetric } from "@/lib/services/metrics";
import { getApiErrorMessage } from "@/lib/utils/errors";

const WRITE_ROLES = ["OWNER", "ADMIN", "BUILDER"];
const CHART_TYPES = [
  { id:"KPI", label:"KPI / Text", icon:"measure" },
  { id:"TABLE", label:"Text table", icon:"table" },
  { id:"BAR", label:"Bars", icon:"chart" },
  { id:"HORIZONTAL_BAR", label:"Horizontal bars", icon:"chart" },
  { id:"STACKED_BAR", label:"Stacked bars", icon:"chart" },
  { id:"SIDE_BY_SIDE_BAR", label:"Side-by-side bars", icon:"chart" },
  { id:"LINE", label:"Line", icon:"activity" },
  { id:"DUAL_LINE", label:"Dual combination", icon:"activity" },
  { id:"AREA", label:"Area", icon:"chart" },
  { id:"PIE", label:"Pie", icon:"dashboard" },
  { id:"DONUT", label:"Donut", icon:"dashboard" },
  { id:"SCATTER", label:"Scatter plot", icon:"explore" },
  { id:"CIRCLE", label:"Circle view", icon:"explore" },
  { id:"SIDE_BY_SIDE_CIRCLE", label:"Side-by-side circles", icon:"explore" },
  { id:"HEATMAP", label:"Heat map", icon:"dashboard" },
  { id:"HIGHLIGHT_TABLE", label:"Highlight table", icon:"table" },
  { id:"TREEMAP", label:"Treemap", icon:"dashboard" },
  { id:"PACKED_BUBBLES", label:"Packed bubbles", icon:"explore" },
  { id:"HISTOGRAM", label:"Histogram", icon:"chart" },
  { id:"BOX_PLOT", label:"Box-and-whisker plot", icon:"chart" },
  { id:"GANTT", label:"Gantt chart", icon:"activity" },
  { id:"BULLET", label:"Bullet graph", icon:"measure" },
  { id:"SYMBOL_MAP", label:"Symbol map", icon:"explore" },
  { id:"FILLED_MAP", label:"Filled map", icon:"explore" },
];

function listValue(value) {
  return Array.isArray(value) ? value : value?.results || [];
}

function fieldLabel(item) {
  return item?.name || item?.field_name || "Field";
}

function recommendChart(dimensions) {
  return dimensions.length ? "BAR" : "KPI";
}

function FieldItem({ item, kind, selected, onClick }) {
  const isDimension = kind === "dimension";
  function dragStart(event) {
    event.dataTransfer.effectAllowed = "copy";
    event.dataTransfer.setData("application/x-bi-field", JSON.stringify({ kind, id: item.id }));
  }
  return (
    <button
      type="button"
      className={`exploreField ${selected ? "selected" : ""}`}
      draggable
      onDragStart={dragStart}
      onClick={onClick}
      title={isDimension ? item.field_name || item.name : item.description || item.name}
    >
      <span className="exploreFieldIcon"><Icon name={isDimension ? "catalog" : "measure"} size={14} /></span>
      <span className="exploreFieldIdentity">
        <strong>{fieldLabel(item)}</strong>
        <small>{isDimension ? item.logical_type || item.dimension_type || "Dimension" : item.aggregation || item.expression_type || "Measure"}</small>
      </span>
      {selected && <span className="exploreFieldCheck">✓</span>}
    </button>
  );
}

function DropZone({ label, hint, emptyText, children, onDrop, compact = false }) {
  const [over, setOver] = useState(false);
  return (
    <div
      className={`exploreDropZone ${compact ? "compact" : ""} ${over ? "isOver" : ""}`}
      onDragOver={(event) => { event.preventDefault(); setOver(true); }}
      onDragLeave={() => setOver(false)}
      onDrop={(event) => {
        event.preventDefault();
        setOver(false);
        try {
          const value = JSON.parse(event.dataTransfer.getData("application/x-bi-field"));
          onDrop?.(value);
        } catch {}
      }}
    >
      <div className="exploreDropHeader"><strong>{label}</strong>{hint && <span>{hint}</span>}</div>
      <div className="exploreDropContent">{children || <span className="exploreDropEmpty">{emptyText}</span>}</div>
    </div>
  );
}

export default function ExploreStudio({ chartId = null }) {
  const { activeWorkspace, organizations } = useWorkspace();
  const [models, setModels] = useState([]);
  const [charts, setCharts] = useState([]);
  const [modelId, setModelId] = useState("");
  const [metricId, setMetricId] = useState("");
  const [dimensionIds, setDimensionIds] = useState([]);
  const [chartType, setChartType] = useState("KPI");
  const [filters, setFilters] = useState([]);
  const [limit, setLimit] = useState(1000);
  const [useCache, setUseCache] = useState(true);
  const [table, setTable] = useState(null);
  const [dataset, setDataset] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [savedChart, setSavedChart] = useState(null);
  const [saveOpen, setSaveOpen] = useState(false);
  const [saveName, setSaveName] = useState("");
  const [savedOpen, setSavedOpen] = useState(false);
  const [fieldSearch, setFieldSearch] = useState("");
  const [rightTab, setRightTab] = useState("visual");
  const [queryVersion, setQueryVersion] = useState(0);
  const [codeOpen,setCodeOpen]=useState(false);
  const [codeLanguage,setCodeLanguage]=useState("SQL");
  const [code,setCode]=useState("");
  const [readingView,setReadingView]=useState(false);
  const [visualSelected,setVisualSelected]=useState(true);
  const autoRunTimer = useRef(null);

  const organization = useMemo(
    () => organizations.find((item) => item.id === activeWorkspace?.organization),
    [organizations, activeWorkspace],
  );
  const canWrite = WRITE_ROLES.includes(organization?.current_user_role);
  const model = useMemo(() => models.find((item) => item.id === modelId), [models, modelId]);
  const metrics = model?.metrics || [];
  const dimensions = model?.dimensions || [];
  const metric = metrics.find((item) => item.id === metricId) || null;
  const selectedDimensions = dimensions.filter((item) => dimensionIds.includes(item.id));

  const filteredDimensions = useMemo(() => {
    const q = fieldSearch.trim().toLowerCase();
    if (!q) return dimensions;
    return dimensions.filter((item) => `${item.name} ${item.field_name || ""} ${item.logical_type || ""}`.toLowerCase().includes(q));
  }, [dimensions, fieldSearch]);
  const filteredMetrics = useMemo(() => {
    const q = fieldSearch.trim().toLowerCase();
    if (!q) return metrics;
    return metrics.filter((item) => `${item.name} ${item.description || ""} ${item.aggregation || ""}`.toLowerCase().includes(q));
  }, [metrics, fieldSearch]);

  async function loadBase() {
    if (!activeWorkspace?.id) { setLoading(false); return; }
    setLoading(true); setError("");
    try {
      const [modelsData, chartsData] = await Promise.all([
        listSemanticModels(activeWorkspace.id),
        listCharts(activeWorkspace.id),
      ]);
      const nextModels = listValue(modelsData).filter((item) => item.enabled !== false);
      setModels(nextModels);
      setCharts(listValue(chartsData));

      let definition = null;
      if (chartId) definition = await getChart(chartId);
      setSavedChart(definition);

      const firstModelId = definition
        ? nextModels.find((item) => item.metrics?.some((candidate) => candidate.id === definition.metric))?.id
        : nextModels[0]?.id;
      const nextModel = nextModels.find((item) => item.id === firstModelId) || nextModels[0];
      setModelId(nextModel?.id || "");
      setMetricId(definition?.metric || nextModel?.metrics?.[0]?.id || "");
      setDimensionIds(definition?.dimensions || []);
      setChartType(definition?.chart_type || recommendChart(definition?.dimensions || []));
      setFilters((definition?.default_filters || []).map((item) => ({ ...item, value: Array.isArray(item.value) ? item.value.join(", ") : item.value })));
      setLimit(definition?.limit || 1000);
      setSaveName(definition?.name || "");
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadBase(); }, [activeWorkspace?.id, chartId]);

  useEffect(() => {
    setDataset(null);
    if (!model?.base_table) { setTable(null); return; }
    getCatalogTable(model.base_table).then(setTable).catch(() => setTable(null));
  }, [model?.base_table]);

  async function runQuery({ silent = false } = {}) {
    if (!metricId) { setDataset(null); return; }
    setRunning(true);
    if (!silent) setError("");
    try {
      const result = await queryMetric(metricId, {
        dimensions: dimensionIds,
        filters: normalizeAnalyticsFilters(filters),
        limit: Number(limit) || 1000,
        use_cache: useCache,
      });
      setDataset(result);
    } catch (requestError) {
      setDataset(null);
      setError(getApiErrorMessage(requestError));
    } finally {
      setRunning(false);
    }
  }

  useEffect(() => {
    if (!metricId || loading) return;
    clearTimeout(autoRunTimer.current);
    autoRunTimer.current = setTimeout(() => runQuery({ silent: true }), 380);
    return () => clearTimeout(autoRunTimer.current);
  }, [metricId, dimensionIds.join("|"), filters, limit, useCache, queryVersion, loading]);

  function selectModel(nextId) {
    const next = models.find((item) => item.id === nextId);
    setModelId(nextId);
    setMetricId(next?.metrics?.[0]?.id || "");
    setDimensionIds([]);
    setFilters([]);
    setChartType("KPI");
    setDataset(null);
    if (!chartId) { setSavedChart(null); setSaveName(""); }
  }

  function selectMetric(nextMetricId) {
    setMetricId(nextMetricId);
    if (!dimensionIds.length) setChartType("KPI");
  }

  function toggleDimension(id) {
    setDimensionIds((current) => {
      const next = current.includes(id) ? current.filter((value) => value !== id) : [...current, id];
      if (!current.length && next.length && chartType === "KPI") setChartType("BAR");
      if (current.length && !next.length && ["BAR", "LINE", "AREA", "PIE", "DONUT", "SCATTER"].includes(chartType)) setChartType("KPI");
      return next;
    });
  }

  function handleDrop(value, zone) {
    if (value.kind === "measure" && zone === "measure") selectMetric(value.id);
    if (value.kind === "dimension" && zone === "dimension" && !dimensionIds.includes(value.id)) {
      setDimensionIds((current) => [...current, value.id]);
      if (chartType === "KPI") setChartType("BAR");
    }
  }

  async function saveAnalysis(event) {
    event.preventDefault();
    if (!canWrite || !metricId || !saveName.trim()) return;
    setSaving(true); setError("");
    const payload = {
      workspace: activeWorkspace.id,
      name: saveName.trim(),
      chart_type: chartType,
      metric: metricId,
      dimensions: dimensionIds,
      config: {},
      default_filters: normalizeAnalyticsFilters(filters),
      sort_order: [],
      limit: Number(limit) || 1000,
    };
    try {
      let saved;
      if (savedChart?.id) {
        saved = await updateChart(savedChart.id, payload);
        setMessage("Análisis actualizado.");
      } else {
        saved = await createChart(payload);
        setMessage("Análisis guardado.");
      }
      setSavedChart(saved);
      setSaveName(saved.name);
      setSaveOpen(false);
      const data = await listCharts(activeWorkspace.id);
      setCharts(listValue(data));
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setSaving(false);
    }
  }

  if (!activeWorkspace) return <EmptyState title="Selecciona un workspace" description="Explore pertenece a un workspace." />;
  if (loading) return <Spinner label="Preparando Explore..." />;

  if (!models.length) {
    return (
      <div className="pageStack">
        <header className="pageHeader"><p className="eyebrow">Analyze</p><h1>Explore</h1><p>Explora métricas visualmente sin crear objetos intermedios antes de tiempo.</p></header>
        {error && <Alert type="error">{error}</Alert>}
        <EmptyState title="No hay modelos semánticos" description="Crea un Semantic Model y al menos una medida para comenzar a explorar." />
        <div className="formActions"><Link href="/app/data-table" className="button primaryButton">Open Data workspace</Link></div>
      </div>
    );
  }

  return (
    <div className="explorePage">
      <header className="exploreTopbar">
        <div className="exploreTitleBlock">
          <p className="eyebrow">Dashboards / Visual Builder</p>
          <div className="exploreTitleRow">
            <h1>{savedChart?.name || "Untitled analysis"}</h1>
            {savedChart && <span className="statusBadge">SAVED</span>}
          </div>
          <p>{model?.name || "Semantic model"} · {metric?.name || "Select a measure"}</p>
        </div>
        <div className="exploreHeaderActions"><button type="button" className="modelIconAction" title="Saved visuals" aria-label="Saved visuals" onClick={() => setSavedOpen((value) => !value)}><Icon name="catalog" size={17}/></button></div>
      </header>

      {error && <Alert type="error">{error}</Alert>}
      {message && <Alert type="success">{message}</Alert>}
      <WorkspaceCommandBar view="analytics" codeOpen={codeOpen} onToggleCode={()=>setCodeOpen(v=>!v)} onSave={()=>{if(!saveName)setSaveName(savedChart?.name||`${metric?.name||"Analysis"} analysis`);setSaveOpen(true)}} onReading={()=>setReadingView(v=>!v)} onRefresh={()=>runQuery()} />
      {codeOpen&&<div className="workspaceCodeRegion"><ScriptWorkbench compact language={codeLanguage} onLanguage={setCodeLanguage} code={code} onCode={setCode} onCommit={()=>setMessage("Code block ready for execution integration.")} /></div>}

      {savedOpen && (
        <section className="exploreSavedPanel">
          <div className="sectionHeading"><div><p className="eyebrow">Library</p><h2>Saved visuals</h2></div><button type="button" className="iconButton" onClick={() => setSavedOpen(false)} aria-label="Close"><Icon name="close" size={16} /></button></div>
          {charts.length ? <div className="exploreSavedGrid">{charts.slice(0, 12).map((item) => <Link key={item.id} href={`/app/analytics/${item.id}`}><span className="resourceIcon"><Icon name="chart" size={16} /></span><span><strong>{item.name}</strong><small>{item.chart_type} · {item.dimensions?.length || 0} dimension(s)</small></span></Link>)}</div> : <p className="mutedText">No saved visuals yet.</p>}
        </section>
      )}

      <div className={`exploreWorkspace tableauWorkspace ${readingView?"readingView":""}`}>
        <aside className="analyticsVisualRail" aria-label="Visuals">{CHART_TYPES.map(item=><button type="button" key={item.id} className={chartType===item.id?"active":""} title={item.label} aria-label={item.label} onClick={()=>{setChartType(item.id);setVisualSelected(true)}}><Icon name={item.icon} size={18}/></button>)}</aside>
        <aside className="exploreDataPane">
          <div className="explorePaneHeader"><span>DATA</span><strong>Fields</strong></div>
          <div className="exploreModelSelect">
            <label>Semantic model</label>
            <select value={modelId} onChange={(event) => selectModel(event.target.value)}>{models.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
          </div>
          <label className="exploreFieldSearch"><Icon name="search" size={14} /><input value={fieldSearch} onChange={(event) => setFieldSearch(event.target.value)} placeholder="Search fields..." /></label>
          <div className="exploreFieldSection">
            <div className="exploreFieldSectionTitle"><span>Dimensions</span><small>{dimensions.length}</small></div>
            <div className="exploreFieldList">{filteredDimensions.length ? filteredDimensions.map((item) => <FieldItem key={item.id} item={item} kind="dimension" selected={dimensionIds.includes(item.id)} onClick={() => toggleDimension(item.id)} />) : <p className="exploreFieldEmpty">No dimensions match.</p>}</div>
          </div>
          <div className="exploreFieldSection">
            <div className="exploreFieldSectionTitle"><span>Measures</span><small>{metrics.length}</small></div>
            <div className="exploreFieldList">{filteredMetrics.length ? filteredMetrics.map((item) => <FieldItem key={item.id} item={item} kind="measure" selected={metricId === item.id} onClick={() => selectMetric(item.id)} />) : <p className="exploreFieldEmpty">No measures match.</p>}</div>
          </div>
          <div className="exploreDataFooter"><Link href="/app/data-table">Manage semantic layer →</Link></div>
        </aside>

        <main className="exploreCanvasPane">
          <div className="exploreEncodingBar">
            <DropZone label="Measure" hint="one" emptyText="Drop a measure" compact onDrop={(value) => handleDrop(value, "measure")}>
              {metric && <button type="button" className="encodingPill measure" onClick={() => setMetricId("")}><Icon name="measure" size={13} /> {metric.name}<span>×</span></button>}
            </DropZone>
            <DropZone label="Dimensions" hint="group by" emptyText="Drop dimensions" compact onDrop={(value) => handleDrop(value, "dimension")}>
              {selectedDimensions.length > 0 && <div className="encodingPillList">{selectedDimensions.map((item) => <button type="button" className="encodingPill" key={item.id} onClick={() => toggleDimension(item.id)}><Icon name="catalog" size={12} /> {item.name}<span>×</span></button>)}</div>}
            </DropZone>
          </div>
          <div className="exploreCanvasHeader">
            <div><strong>{metric?.name || "Choose a measure"}</strong><span>{selectedDimensions.length ? `by ${selectedDimensions.map((item) => item.name).join(" · ")}` : "Overall value"}</span></div>
            <div className="exploreQueryMeta">{running ? <span className="runningDot">● Running</span> : dataset ? <><span>{dataset.returned ?? 0} row(s)</span><span>·</span><span>{dataset.cached ? "cache" : "fresh query"}</span></> : <span>Ready</span>}</div>
          </div>
          <div className={`exploreCanvas analyticsVisualBlock ${visualSelected?"selected":""} ${running && !dataset ? "isLoading" : ""}`} onClick={()=>setVisualSelected(true)}>
            {!metric ? <div className="exploreCanvasEmpty"><span className="emptyVisualIcon"><Icon name="explore" size={28} /></span><strong>Select a measure to start</strong><span>Choose a measure from the Data pane, then add dimensions to break it down.</span></div> : running && !dataset ? <Spinner label="Querying measure..." /> : dataset ? <ChartRenderer chart={{ chart_type: chartType, name: savedChart?.name || metric.name }} dataset={dataset} /> : <div className="exploreCanvasEmpty"><strong>No result yet</strong><button type="button" className="button secondaryButton" onClick={() => runQuery()}>Run query</button></div>}
          </div>
          <div className="exploreCanvasFooter"><span>Changes run automatically.</span><span>{table ? table.table_name : model?.name}</span></div>
        </main>

        <aside className={`explorePropertiesPane ${visualSelected?"":"noSelection"}`}>
          <div className="explorePropertiesTabs">
            <button type="button" className={rightTab === "visual" ? "active" : ""} onClick={() => setRightTab("visual")}>Visual</button>
            <button type="button" className={rightTab === "filters" ? "active" : ""} onClick={() => setRightTab("filters")}>Filters {filters.length ? `(${filters.length})` : ""}</button>
            <button type="button" className={rightTab === "query" ? "active" : ""} onClick={() => setRightTab("query")}>Query</button>
          </div>

          {rightTab === "visual" && <div className="explorePropertiesBody">
            <section className="propertySection"><div className="propertyTitle"><strong>Visualization</strong><span>{CHART_TYPES.find(item=>item.id===chartType)?.label||chartType}</span></div><p className="mutedText">Select another visual from the left rail. Properties remain contextual to the selected visual.</p></section>
            <section className="propertySection"><div className="propertyTitle"><strong>Fields</strong><span>Click fields or drag them from the Data pane.</span></div><DropZone label="Measure" emptyText="Choose measure" onDrop={(value) => handleDrop(value, "measure")}>{metric && <button type="button" className="encodingPill measure" onClick={() => setMetricId("")}>{metric.name}<span>×</span></button>}</DropZone><DropZone label="Dimensions" emptyText="Add dimensions" onDrop={(value) => handleDrop(value, "dimension")}>{selectedDimensions.length > 0 && <div className="encodingPillList">{selectedDimensions.map((item) => <button type="button" className="encodingPill" key={item.id} onClick={() => toggleDimension(item.id)}>{item.name}<span>×</span></button>)}</div>}</DropZone></section>
          </div>}

          {rightTab === "filters" && <div className="explorePropertiesBody"><section className="propertySection"><div className="propertyTitle"><strong>Runtime filters</strong><span>Filter the underlying table without changing the semantic definition.</span></div>{table?.fields?.length ? <AnalyticsFilterBuilder fields={table.fields} filters={filters} onChange={setFilters} /> : <p className="mutedText">Table fields are unavailable for this model.</p>}</section></div>}

          {rightTab === "query" && <div className="explorePropertiesBody"><section className="propertySection"><div className="propertyTitle"><strong>Query behavior</strong><span>Control result size and cache behavior.</span></div><label className="propertyField">Row limit<input type="number" min="1" max="5000" value={limit} onChange={(event) => setLimit(event.target.value)} /></label><label className="propertyCheck"><input type="checkbox" checked={useCache} onChange={(event) => setUseCache(event.target.checked)} /> Use metric cache</label><button type="button" className="button secondaryButton wideButton" onClick={() => { setQueryVersion((value) => value + 1); runQuery(); }} disabled={running || !metricId}>Run fresh preview</button></section><section className="propertySection"><div className="propertyTitle"><strong>Semantic context</strong></div><dl className="propertyDetails"><div><dt>Model</dt><dd>{model?.name}</dd></div><div><dt>Measure</dt><dd>{metric?.name || "—"}</dd></div><div><dt>Dimensions</dt><dd>{dimensionIds.length}</dd></div><div><dt>Base table</dt><dd>{table ? table.table_name : "—"}</dd></div></dl></section></div>}
        </aside>
      </div>

      {saveOpen && <div className="modalBackdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setSaveOpen(false); }}><form className="modalCard exploreSaveModal" onSubmit={saveAnalysis}><div className="cardHeader"><div><p className="eyebrow">Persist analysis</p><h2>{savedChart ? "Update analysis" : "Save analysis"}</h2><p>The current visual, dimensions and filters become a reusable ChartDefinition.</p></div><button type="button" className="iconButton" onClick={() => setSaveOpen(false)}><Icon name="close" size={16} /></button></div><label>Name<input autoFocus value={saveName} onChange={(event) => setSaveName(event.target.value)} placeholder="e.g. Revenue by month" required /></label><div className="exploreSaveSummary"><span>{chartType}</span><span>{metric?.name}</span><span>{dimensionIds.length} dimension(s)</span><span>{filters.length} filter(s)</span></div><div className="formActions"><button type="button" className="button secondaryButton" onClick={() => setSaveOpen(false)}>Cancel</button><button type="submit" className="button primaryButton" disabled={saving || !saveName.trim()}>{saving ? "Saving..." : savedChart ? "Update analysis" : "Save analysis"}</button></div></form></div>}
    </div>
  );
}
