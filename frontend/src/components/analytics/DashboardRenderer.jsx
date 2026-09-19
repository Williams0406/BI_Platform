"use client";
import ChartRenderer from "@/components/analytics/ChartRenderer";

function itemStyle(position={}) {
  const w=Math.max(1,Math.min(Number(position.w)||6,12));
  return { gridColumn:`span ${w}` };
}

export default function DashboardRenderer({ data }) {
  if(!data?.items?.length)return <p className="mutedText">El dashboard no contiene items o no devolvió datos.</p>;
  return <div className="dashboardCanvas">{data.items.map(item=><article className="dashboardTile" key={item.item_id} style={itemStyle(item.position)}><header><div><strong>{item.title_override||item.chart?.name}</strong><small>{item.chart?.chart_type}</small></div><span>{item.dataset?.cached?"cache":"live"}</span></header><ChartRenderer chart={item.chart} dataset={item.dataset} title={item.title_override}/></article>)}</div>;
}
