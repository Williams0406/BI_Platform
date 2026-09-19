"use client";

import { useMemo, useState } from "react";

export default function DependencyForm({ workspaceId, assets, onSubmit, onCancel, isSaving }) {
  const [upstream, setUpstream] = useState("");
  const [downstream, setDownstream] = useState("");
  const [dependencyType, setDependencyType] = useState("DATA");
  const [refreshPolicy, setRefreshPolicy] = useState("MARK_STALE");
  const [metadata, setMetadata] = useState("{}");
  const availableDownstream = useMemo(() => assets.filter((item) => item.id !== upstream), [assets, upstream]);

  function submit(event) {
    event.preventDefault();
    let parsed = {};
    try { parsed = JSON.parse(metadata || "{}"); } catch { window.alert("Metadata debe ser JSON válido."); return; }
    onSubmit({ workspace: workspaceId, upstream, downstream, dependency_type: dependencyType, refresh_policy: refreshPolicy, metadata: parsed });
  }

  return <form className="formStack" onSubmit={submit}>
    <div className="formGrid twoColumns">
      <label className="field"><span>Upstream</span><select required value={upstream} onChange={(e) => { setUpstream(e.target.value); if (e.target.value === downstream) setDownstream(""); }}><option value="">Seleccionar asset...</option>{assets.map((asset) => <option key={asset.id} value={asset.id}>{asset.name} · {asset.asset_type}</option>)}</select></label>
      <label className="field"><span>Downstream</span><select required value={downstream} onChange={(e) => setDownstream(e.target.value)}><option value="">Seleccionar asset...</option>{availableDownstream.map((asset) => <option key={asset.id} value={asset.id}>{asset.name} · {asset.asset_type}</option>)}</select></label>
      <label className="field"><span>Tipo</span><select value={dependencyType} onChange={(e) => setDependencyType(e.target.value)}><option value="DATA">DATA</option><option value="CALCULATION">CALCULATION</option><option value="MODEL_INPUT">MODEL_INPUT</option><option value="VISUALIZATION">VISUALIZATION</option></select></label>
      <label className="field"><span>Refresh policy</span><select value={refreshPolicy} onChange={(e) => setRefreshPolicy(e.target.value)}><option value="AUTO">AUTO</option><option value="MARK_STALE">MARK_STALE</option><option value="MANUAL">MANUAL</option></select></label>
    </div>
    <label className="field"><span>Metadata JSON</span><textarea className="codeArea" rows="4" value={metadata} onChange={(e) => setMetadata(e.target.value)} /></label>
    <div className="formActions"><button type="button" className="button secondaryButton" onClick={onCancel}>Cancelar</button><button type="submit" className="button primaryButton" disabled={isSaving}>{isSaving ? "Guardando..." : "Crear dependencia"}</button></div>
  </form>;
}
