export default function ModelMetrics({ metrics = {} }) {
  const entries = Object.entries(metrics || {});
  if (!entries.length) return <span className="mutedText">Sin métricas todavía.</span>;
  return <div className="mlMetricsGrid">{entries.map(([key,value])=><div className="mlMetric" key={key}><span>{key.replaceAll("_"," ")}</span><strong>{typeof value === "number" ? value.toFixed(4).replace(/\.0000$/,".0000") : String(value)}</strong></div>)}</div>;
}
