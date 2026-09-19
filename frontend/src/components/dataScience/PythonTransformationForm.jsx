"use client";

import { useEffect, useState } from "react";

const PACKAGE_OPTIONS = ["pandas", "numpy", "math", "statistics", "datetime", "json"];

const DEFAULT_CODE = `df = table("input")\n\n# Transforma el DataFrame usando pandas.\nresult = df.copy()\n\nsave_table(result)`;

export default function PythonTransformationForm({ workspaceId, initialValue, onSubmit, onCancel, isSaving }) {
  const [form, setForm] = useState({
    name: "",
    description: "",
    code: DEFAULT_CODE,
    output_name: "",
    allowed_packages: ["pandas"],
    timeout_seconds: 300,
    memory_limit_mb: 1024,
    max_input_rows: 100000,
    enabled: true,
  });

  useEffect(() => {
    setForm({
      name: initialValue?.name || "",
      description: initialValue?.description || "",
      code: initialValue?.code || DEFAULT_CODE,
      output_name: initialValue?.output_name || "",
      allowed_packages: initialValue?.allowed_packages || ["pandas"],
      timeout_seconds: initialValue?.timeout_seconds ?? 300,
      memory_limit_mb: initialValue?.memory_limit_mb ?? 1024,
      max_input_rows: initialValue?.max_input_rows ?? 100000,
      enabled: initialValue?.enabled ?? true,
    });
  }, [initialValue]);

  function set(key, value) { setForm((old) => ({ ...old, [key]: value })); }
  function togglePackage(value) {
    set("allowed_packages", form.allowed_packages.includes(value)
      ? form.allowed_packages.filter((item) => item !== value)
      : [...form.allowed_packages, value]);
  }

  function submit(event) {
    event.preventDefault();
    onSubmit({
      workspace: workspaceId,
      ...form,
      timeout_seconds: Number(form.timeout_seconds) || 300,
      memory_limit_mb: Number(form.memory_limit_mb) || 1024,
      max_input_rows: Number(form.max_input_rows) || 100000,
    });
  }

  return <form className="formGrid" onSubmit={submit}>
    <label className="fieldGroup"><span>Nombre</span><input value={form.name} onChange={(e)=>set("name",e.target.value)} required /></label>
    <label className="fieldGroup"><span>Nombre del output</span><input value={form.output_name} onChange={(e)=>set("output_name",e.target.value)} required placeholder="dataset_transformado" /></label>
    <label className="fieldGroup fullWidth"><span>Descripción</span><textarea rows="2" value={form.description} onChange={(e)=>set("description",e.target.value)} /></label>
    <div className="fieldGroup fullWidth"><span>Packages permitidos</span><div className="checkGrid">{PACKAGE_OPTIONS.map((item)=><label className="checkField" key={item}><input type="checkbox" checked={form.allowed_packages.includes(item)} onChange={()=>togglePackage(item)} /> {item}</label>)}</div><small>El backend vuelve a validar la whitelist global antes de ejecutar.</small></div>
    <label className="fieldGroup"><span>Timeout (seg.)</span><input type="number" min="1" value={form.timeout_seconds} onChange={(e)=>set("timeout_seconds",e.target.value)} /></label>
    <label className="fieldGroup"><span>Memoria máxima (MB)</span><input type="number" min="64" value={form.memory_limit_mb} onChange={(e)=>set("memory_limit_mb",e.target.value)} /></label>
    <label className="fieldGroup"><span>Máx. filas por input</span><input type="number" min="1" value={form.max_input_rows} onChange={(e)=>set("max_input_rows",e.target.value)} /></label>
    <label className="checkField"><input type="checkbox" checked={form.enabled} onChange={(e)=>set("enabled",e.target.checked)} /> Habilitada</label>
    <label className="fieldGroup fullWidth"><span>Código Python</span><textarea className="codeArea pythonEditor" rows="15" value={form.code} onChange={(e)=>set("code",e.target.value)} required /><small>Usa <code>table("alias")</code> para leer inputs y termina con <code>save_table(dataframe)</code>.</small></label>
    <div className="formActions fullWidth"><button type="button" className="button secondaryButton" onClick={onCancel}>Cancelar</button><button type="submit" className="button primaryButton" disabled={isSaving}>{isSaving?"Guardando...":"Guardar"}</button></div>
  </form>;
}
