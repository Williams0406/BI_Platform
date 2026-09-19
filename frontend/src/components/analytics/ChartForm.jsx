"use client";

import { useEffect, useMemo, useState } from "react";
import Alert from "@/components/ui/Alert";

const CHART_TYPES = ["KPI", "TABLE", "BAR", "LINE", "AREA", "PIE", "DONUT", "SCATTER"];

function jsonText(value, fallback) {
  try { return JSON.stringify(value ?? fallback, null, 2); } catch { return JSON.stringify(fallback, null, 2); }
}

export default function ChartForm({ workspaceId, metrics = [], models = [], initialValue, onSubmit, onCancel, isSaving }) {
  const [name, setName] = useState("");
  const [chartType, setChartType] = useState("BAR");
  const [metricId, setMetricId] = useState("");
  const [dimensions, setDimensions] = useState([]);
  const [limit, setLimit] = useState(1000);
  const [config, setConfig] = useState("{}");
  const [defaultFilters, setDefaultFilters] = useState("[]");
  const [sortOrder, setSortOrder] = useState("[]");
  const [error, setError] = useState("");

  useEffect(() => {
    setName(initialValue?.name || "");
    setChartType(initialValue?.chart_type || "BAR");
    setMetricId(initialValue?.metric || metrics[0]?.id || "");
    setDimensions(initialValue?.dimensions || []);
    setLimit(initialValue?.limit || 1000);
    setConfig(jsonText(initialValue?.config, {}));
    setDefaultFilters(jsonText(initialValue?.default_filters, []));
    setSortOrder(jsonText(initialValue?.sort_order, []));
    setError("");
  }, [initialValue, metrics]);

  const metric = metrics.find((item) => item.id === metricId);
  const model = models.find((item) => item.id === metric?.semantic_model);
  const availableDimensions = model?.dimensions || [];

  useEffect(() => {
    if (!metricId) return;
    const allowed = new Set(availableDimensions.map((item) => item.id));
    setDimensions((current) => current.filter((id) => allowed.has(id)));
  }, [metricId]);

  function toggleDimension(id) {
    setDimensions((current) => (current.includes(id) ? current.filter((value) => value !== id) : [...current, id]));
  }

  function submit(event) {
    event.preventDefault();
    setError("");
    try {
      const parsedConfig = JSON.parse(config || "{}");
      const parsedFilters = JSON.parse(defaultFilters || "[]");
      const parsedSort = JSON.parse(sortOrder || "[]");
      if (!Array.isArray(parsedFilters) || !Array.isArray(parsedSort)) throw new Error("default_filters y sort_order deben ser listas JSON.");
      onSubmit({
        workspace: workspaceId,
        name: name.trim(),
        chart_type: chartType,
        metric: metricId,
        dimensions,
        config: parsedConfig,
        default_filters: parsedFilters,
        sort_order: parsedSort,
        limit: Number(limit),
      });
    } catch (requestError) {
      setError(requestError.message || "JSON inválido.");
    }
  }

  return (
    <form className="formGrid" onSubmit={submit}>
      {error && <Alert type="error">{error}</Alert>}
      <label>Nombre<input value={name} onChange={(e) => setName(e.target.value)} required /></label>
      <label>Tipo<select value={chartType} onChange={(e) => setChartType(e.target.value)}>{CHART_TYPES.map((type) => <option key={type}>{type}</option>)}</select></label>
      <label className="span2">Métrica<select value={metricId} onChange={(e) => setMetricId(e.target.value)} required><option value="">Selecciona...</option>{metrics.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
      <div className="span2 metricDimensionPicker"><strong>Dimensiones</strong><p className="mutedText">Solo aparecen dimensiones del Semantic Model de la métrica.</p><div className="chipList">{availableDimensions.map((dimension) => <button type="button" key={dimension.id} className={`chipButton ${dimensions.includes(dimension.id) ? "activeChip" : ""}`} onClick={() => toggleDimension(dimension.id)}>{dimension.name}</button>)}</div></div>
      <label>Limit<input type="number" min="1" max="5000" value={limit} onChange={(e) => setLimit(e.target.value)} /></label>
      <div />
      <label className="span2">Config JSON<textarea rows="5" value={config} onChange={(e) => setConfig(e.target.value)} /></label>
      <label className="span2">Default filters JSON<textarea rows="5" value={defaultFilters} onChange={(e) => setDefaultFilters(e.target.value)} /></label>
      <label className="span2">Sort order JSON<textarea rows="4" value={sortOrder} onChange={(e) => setSortOrder(e.target.value)} /></label>
      <div className="formActions span2"><button type="button" className="button secondaryButton" onClick={onCancel}>Cancelar</button><button type="submit" className="button primaryButton" disabled={isSaving || !metricId}>{isSaving ? "Guardando..." : "Guardar gráfico"}</button></div>
    </form>
  );
}
