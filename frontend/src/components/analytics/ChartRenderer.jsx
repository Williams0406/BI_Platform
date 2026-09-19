"use client";

function formatMetricValue(value, metric = {}) {
  if (value === null || value === undefined) return "—";
  const number = Number(value);
  if (Number.isNaN(number)) return String(value);
  const decimals = metric.decimal_places ?? 2;
  if (metric.format_type === "PERCENT") return `${(number * 100).toFixed(decimals)}%`;
  if (metric.format_type === "INTEGER") return Math.round(number).toLocaleString();
  const formatted = number.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  return metric.unit ? `${metric.unit} ${formatted}` : formatted;
}

function prepare(dataset) {
  const rows = dataset?.rows || [];
  const dimensions = dataset?.dimensions || [];
  const labels = rows.map((row, index) => {
    if (!dimensions.length) return `#${index + 1}`;
    return dimensions.map((dimension) => String(row[dimension.id] ?? "—")).join(" · ");
  });
  const values = rows.map((row) => Number(row.value) || 0);
  return { rows, dimensions, labels, values };
}
function mix(hex, target, weight) {
  const clean = String(hex || "#4d6072").replace("#", "");
  const base = clean.length === 3 ? clean.split("").map((x) => x + x).join("") : clean.padEnd(6, "0").slice(0, 6);
  const rgb = [0, 2, 4].map((index) => parseInt(base.slice(index, index + 2), 16));
  const targetRgb = target === "white" ? [255, 255, 255] : [0, 0, 0];
  return `#${rgb.map((value, index) => Math.round(value + (targetRgb[index] - value) * weight).toString(16).padStart(2, "0")).join("")}`;
}
function palette(accent) {
  return [accent, mix(accent, "white", .22), mix(accent, "black", .18), mix(accent, "white", .42), mix(accent, "black", .34), mix(accent, "white", .6), mix(accent, "black", .48), mix(accent, "white", .72)];
}

function TableChart({ dataset, style }) {
  const { rows, dimensions } = prepare(dataset);
  return <div className="tableWrap"><table className="dataTable powerStyledTable" style={{ fontSize: style.fontSize }}><thead><tr>{dimensions.map((d) => <th key={d.id}>{d.name}</th>)}<th>{dataset?.metric?.name || "Value"}</th></tr></thead><tbody>{rows.map((row, index) => <tr key={index}>{dimensions.map((d) => <td key={d.id}>{String(row[d.id] ?? "—")}</td>)}<td><strong>{formatMetricValue(row.value, dataset?.metric)}</strong></td></tr>)}</tbody></table></div>;
}

function CartesianChart({ dataset, mode, style }) {
  const { labels, values } = prepare(dataset);
  if (!values.length) return <p className="mutedText">Sin datos.</p>;
  const width = 760, height = 300, pad = 44, plotW = width - pad * 2, plotH = height - pad * 2;
  const min = Math.min(0, ...values), max = Math.max(0, ...values), range = max - min || 1;
  const y = (v) => pad + plotH - ((v - min) / range) * plotH;
  const step = plotW / Math.max(values.length, 1);
  const points = values.map((v, i) => `${pad + step * i + step / 2},${y(v)}`).join(" ");
  const grid = [0.25, 0.5, 0.75].map((portion) => pad + plotH * portion);
  return <div className="svgChartWrap"><svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={mode} style={{ fontFamily: style.fontFamily }}>
    {style.showGridlines && grid.map((gy) => <line key={gy} x1={pad} y1={gy} x2={width - pad} y2={gy} className="chartGridLine" />)}
    <line x1={pad} y1={pad} x2={pad} y2={height - pad} className="chartAxis" /><line x1={pad} y1={height - pad} x2={width - pad} y2={height - pad} className="chartAxis" />
    {mode === "BAR" && values.map((v, i) => { const x = pad + step * i + step * .15; const baseline = y(0); const yy = Math.min(y(v), baseline); const h = Math.max(Math.abs(baseline - y(v)), 1); return <g key={i}><rect x={x} y={yy} width={step * .7} height={h} fill={style.accentColor}><title>{labels[i]}: {formatMetricValue(v, dataset.metric)}</title></rect>{style.showDataLabels && <text x={x + step * .35} y={Math.max(yy - 5, 12)} textAnchor="middle" className="chartDataLabel" style={{ fontSize: style.fontSize }}>{formatMetricValue(v, dataset.metric)}</text>}</g>; })}
    {(mode === "LINE" || mode === "AREA") && <>{mode === "AREA" && <polygon points={`${pad + step / 2},${height - pad} ${points} ${pad + step * (values.length - 1) + step / 2},${height - pad}`} fill={mix(style.accentColor, "white", .7)} />}<polyline points={points} fill="none" stroke={style.accentColor} strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />{values.map((v, i) => <g key={i}><circle cx={pad + step * i + step / 2} cy={y(v)} r="4" fill={style.accentColor}><title>{labels[i]}: {formatMetricValue(v, dataset.metric)}</title></circle>{style.showDataLabels && <text x={pad + step * i + step / 2} y={Math.max(y(v) - 10, 12)} textAnchor="middle" className="chartDataLabel" style={{ fontSize: style.fontSize }}>{formatMetricValue(v, dataset.metric)}</text>}</g>)}</>}
    {labels.map((label, i) => <text key={i} x={pad + step * i + step / 2} y={height - 12} textAnchor="middle" className="chartTick" style={{ fontSize: style.fontSize }}>{label.length > 12 ? `${label.slice(0, 10)}…` : label}</text>)}
  </svg></div>;
}

function PieChart({ dataset, donut = false, style }) {
  const { labels, values } = prepare(dataset);
  const positive = values.map((v) => Math.max(v, 0));
  const total = positive.reduce((a, b) => a + b, 0);
  if (!total) return <p className="mutedText">Sin valores positivos para representar.</p>;
  const colors = palette(style.accentColor);
  const cx = 160, cy = 160, r = 120;
  let angle = -Math.PI / 2;
  const slices = positive.map((value, index) => { const start = angle; const delta = value / total * Math.PI * 2; const end = start + delta; angle = end; const x1 = cx + r * Math.cos(start), y1 = cy + r * Math.sin(start), x2 = cx + r * Math.cos(end), y2 = cy + r * Math.sin(end); const large = delta > Math.PI ? 1 : 0; return { index, value, path: `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z` }; });
  return <div className="pieLayout"><svg viewBox="0 0 320 320" className="pieSvg">{slices.map((slice) => <path key={slice.index} d={slice.path} fill={colors[slice.index % colors.length]}><title>{labels[slice.index]}: {formatMetricValue(slice.value, dataset.metric)}</title></path>)}{donut && <circle cx={cx} cy={cy} r="62" fill={style.backgroundColor} />}</svg>{style.showLegend && <div className="chartLegend" style={{ fontSize: style.fontSize }}>{labels.map((label, i) => <div key={i}><span className="legendSwatch" style={{ background: colors[i % colors.length] }} /><span>{label}</span><strong>{formatMetricValue(values[i], dataset.metric)}</strong></div>)}</div>}</div>;
}

function ScatterChart({ dataset, style }) {
  const { rows, dimensions } = prepare(dataset);
  if (!rows.length) return <p className="mutedText">Sin datos.</p>;
  const first = dimensions[0];
  const points = rows.map((row, index) => ({ x: Number(row[first?.id]), y: Number(row.value), label: first ? String(row[first.id]) : `#${index + 1}` }));
  const numeric = points.every((point) => Number.isFinite(point.x));
  if (!numeric) points.forEach((point, index) => { point.x = index + 1; });
  const xs = points.map((point) => point.x), ys = points.map((point) => point.y);
  const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(0, ...ys), maxY = Math.max(0, ...ys);
  const w = 760, h = 300, pad = 44;
  const x = (v) => pad + ((v - minX) / (maxX - minX || 1)) * (w - pad * 2);
  const y = (v) => pad + (h - pad * 2) - ((v - minY) / (maxY - minY || 1)) * (h - pad * 2);
  return <div className="svgChartWrap"><svg viewBox={`0 0 ${w} ${h}`} style={{ fontFamily: style.fontFamily }}>{style.showGridlines && [0.25, .5, .75].map((portion) => <line key={portion} x1={pad} y1={pad + (h - pad * 2) * portion} x2={w - pad} y2={pad + (h - pad * 2) * portion} className="chartGridLine" />)}<line x1={pad} y1={pad} x2={pad} y2={h - pad} className="chartAxis" /><line x1={pad} y1={h - pad} x2={w - pad} y2={h - pad} className="chartAxis" />{points.map((point, i) => <circle key={i} cx={x(point.x)} cy={y(point.y)} r="6" fill={style.accentColor}><title>{point.label}: {formatMetricValue(point.y, dataset.metric)}</title></circle>)}</svg>{!numeric && <p className="mutedText">SCATTER uses a categorical index on X because the first dimension is not numeric.</p>}</div>;
}

function SlicerChart({ dataset, style, binding, activeValue, onSelect }) {
  const { rows, dimensions } = prepare(dataset);
  const dimension = dimensions[0];
  if (!binding || !dimension) return <div className="slicerEmptyState">Drag a field into the Slicer field well.</div>;
  const values = [...new Set(rows.map((row) => row[dimension.id]).filter((value) => value !== null && value !== undefined))];
  if (!values.length) return <p className="mutedText">Sin valores para filtrar.</p>;
  return <div className="slicerVisual" style={{ fontFamily: style.fontFamily, fontSize: style.fontSize }}>
    <div className="slicerVisualTitle">{binding.label || dimension.name}</div>
    <div className="slicerOptions">
      {values.map((value) => { const selected = String(activeValue ?? "") === String(value); return (
        <button key={String(value)} type="button" className={selected ? "selected" : ""} onClick={(event) => { event.stopPropagation(); onSelect?.(binding.fieldName, value); }}>
          <span className="slicerCheck">{selected ? "✓" : ""}</span><span>{String(value)}</span>
        </button>
      ); })}
    </div>
  </div>;
}


function BubbleChart({dataset,style,packed=false}){const {labels,values}=prepare(dataset);const max=Math.max(...values.map(v=>Math.abs(v)),1);return <div className="bubbleChart">{values.map((v,i)=><div key={i} className="bubbleMark" style={{width:packed?Math.max(44,110*Math.sqrt(Math.abs(v)/max)):48,height:packed?Math.max(44,110*Math.sqrt(Math.abs(v)/max)):48,background:palette(style.accentColor)[i%8]}} title={`${labels[i]}: ${formatMetricValue(v,dataset.metric)}`}><span>{labels[i]}</span></div>)}</div>}
function HeatChart({dataset,style,highlight=false}){const {labels,values}=prepare(dataset);const max=Math.max(...values.map(v=>Math.abs(v)),1);return <div className={`heatChart ${highlight?"highlight":""}`}>{values.map((v,i)=><div key={i} style={{background:mix(style.accentColor,"white",.82*(1-Math.abs(v)/max))}}><span>{labels[i]}</span><strong>{formatMetricValue(v,dataset.metric)}</strong></div>)}</div>}
function BulletChart({dataset,style}){const {labels,values}=prepare(dataset);const max=Math.max(...values.map(v=>Math.abs(v)),1);return <div className="bulletChart">{values.map((v,i)=><div key={i}><span>{labels[i]}</span><i><b style={{width:`${Math.abs(v)/max*100}%`,background:style.accentColor}}/></i><strong>{formatMetricValue(v,dataset.metric)}</strong></div>)}</div>}

export default function ChartRenderer({ chart, dataset, title, visualStyle = {}, visualType = null, slicerBinding = null, activeSlicerValue = null, onSlicerSelect = null }) {
  const style = {
    backgroundColor: "#ffffff",
    accentColor: "#4d6072",
    textColor: "#1f2937",
    fontFamily: "Inter, system-ui, sans-serif",
    fontSize: 12,
    showLegend: true,
    showDataLabels: false,
    showGridlines: true,
    ...visualStyle,
  };
  const type = visualType || chart?.chart_type || "TABLE";
  if (!dataset) return <p className="mutedText">Ejecuta el dataset para visualizar el gráfico.</p>;
  const wrapStyle = { color: style.textColor, fontFamily: style.fontFamily, fontSize: style.fontSize };
  if (type === "SLICER") return <div style={wrapStyle}><SlicerChart dataset={dataset} style={style} binding={slicerBinding} activeValue={activeSlicerValue} onSelect={onSlicerSelect} /></div>;
  if (type === "KPI") return <div className="kpiVisual" style={wrapStyle}><span>{title || chart?.name || dataset?.metric?.name}</span><strong style={{ color: style.accentColor, fontFamily: style.fontFamily }}>{formatMetricValue(dataset.rows?.[0]?.value, dataset.metric)}</strong><small>{dataset.cached ? "cache" : "consulta nueva"}</small></div>;
  if (type === "TABLE") return <div style={wrapStyle}><TableChart dataset={dataset} style={style} /></div>;
  if (["BAR", "HORIZONTAL_BAR", "STACKED_BAR", "SIDE_BY_SIDE_BAR", "HISTOGRAM", "GANTT"].includes(type)) return <div style={wrapStyle}><CartesianChart dataset={dataset} mode="BAR" style={style} /></div>;
  if (["LINE","DUAL_LINE","AREA"].includes(type)) return <div style={wrapStyle}><CartesianChart dataset={dataset} mode={type==="AREA"?"AREA":"LINE"} style={style} /></div>;
  if (type === "PIE") return <div style={wrapStyle}><PieChart dataset={dataset} style={style} /></div>;
  if (type === "DONUT") return <div style={wrapStyle}><PieChart dataset={dataset} donut style={style} /></div>;
  if (["SCATTER","BOX_PLOT","SYMBOL_MAP","FILLED_MAP"].includes(type)) return <div style={wrapStyle}><ScatterChart dataset={dataset} style={style} /></div>;
  if (["CIRCLE","SIDE_BY_SIDE_CIRCLE","PACKED_BUBBLES","TREEMAP"].includes(type)) return <div style={wrapStyle}><BubbleChart dataset={dataset} style={style} packed={type!=="CIRCLE"}/></div>;
  if (["HEATMAP","HIGHLIGHT_TABLE"].includes(type)) return <div style={wrapStyle}><HeatChart dataset={dataset} style={style} highlight={type==="HIGHLIGHT_TABLE"}/></div>;
  if (type==="BULLET") return <div style={wrapStyle}><BulletChart dataset={dataset} style={style}/></div>;
  return <div style={wrapStyle}><TableChart dataset={dataset} style={style} /></div>;
}

export { formatMetricValue };
