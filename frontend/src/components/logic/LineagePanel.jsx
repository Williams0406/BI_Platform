export default function LineagePanel({ lineage }) {
  if (!lineage) return null;
  return <div className="lineagePanel">
    <div><h3>Upstream</h3>{lineage.upstream?.length ? lineage.upstream.map((item) => <div className="lineageNode" key={item.id}><strong>{item.name}</strong><small>{item.dependency_type} · {item.refresh_policy}</small></div>) : <p className="mutedText">Sin dependencias upstream.</p>}</div>
    <div className="lineageCenter"><span>→</span><strong>{lineage.asset?.name}</strong><small>{lineage.asset?.type}</small><span>→</span></div>
    <div><h3>Downstream</h3>{lineage.downstream?.length ? lineage.downstream.map((item) => <div className="lineageNode" key={item.id}><strong>{item.name}</strong><small>{item.dependency_type} · {item.refresh_policy}</small></div>) : <p className="mutedText">Sin dependencias downstream.</p>}</div>
  </div>;
}
