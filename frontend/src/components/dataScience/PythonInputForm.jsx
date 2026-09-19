"use client";

import { useMemo, useState } from "react";

export default function PythonInputForm({ assets, existingInputs = [], onSubmit, isSaving }) {
  const usedAssets = useMemo(() => new Set(existingInputs.map((item) => item.asset)), [existingInputs]);
  const usedAliases = useMemo(() => new Set(existingInputs.map((item) => item.alias)), [existingInputs]);
  const available = assets.filter((item) => !usedAssets.has(item.id));
  const [asset, setAsset] = useState(available[0]?.id || "");
  const [alias, setAlias] = useState("");

  function submit(event) {
    event.preventDefault();
    const cleanAlias = alias.trim();
    if (!asset || !cleanAlias || usedAliases.has(cleanAlias)) return;
    onSubmit({ asset, alias: cleanAlias }).then?.(() => { setAlias(""); });
  }

  return <form className="inlineForm" onSubmit={submit}>
    <label className="fieldGroup growField"><span>Data Asset tabular MANAGED</span><select value={asset} onChange={(e)=>setAsset(e.target.value)} required><option value="">Seleccionar</option>{available.map((item)=><option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
    <label className="fieldGroup"><span>Alias Python</span><input value={alias} onChange={(e)=>setAlias(e.target.value.replace(/[^A-Za-z0-9_]/g,"_"))} placeholder="orders" required /></label>
    <button type="submit" className="button primaryButton" disabled={isSaving || !available.length || usedAliases.has(alias.trim())}>Agregar input</button>
  </form>;
}
