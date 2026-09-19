"use client";

import { useMemo, useState } from "react";
import { normalizeTechnicalName } from "@/lib/tableIdentity";

const LOGICAL_TYPES = [
  "BIGINT", "BINARY", "BOOLEAN", "DATE", "DATETIME", "DATETIME_TZ",
  "DECIMAL", "FLOAT", "INTEGER", "JSON", "STRING", "TEXT", "TIME", "UUID",
];

function newField(index) {
  return {
    key: `${Date.now()}-${index}`,
    name: "",
    logical_type: "STRING",
    nullable: true,
    unique: false,
    has_default: false,
    default: "",
    max_length: 255,
    numeric_precision: 18,
    numeric_scale: 2,
    is_identity: false,
    is_primary_key: false,
  };
}

function newForeignKey(index) {
  return {
    key: `fk-${Date.now()}-${index}`,
    source_columns_text: "",
    target_table_asset: "",
    target_columns_text: "",
    on_delete: "NO ACTION",
  };
}

function parseDefault(field) {
  if (!field.has_default) return undefined;
  const raw = field.default;
  if (raw === "") return "";
  if (field.logical_type === "BOOLEAN") return String(raw).toLowerCase() === "true";
  if (["INTEGER", "BIGINT"].includes(field.logical_type)) return Number.parseInt(raw, 10);
  if (["FLOAT", "DECIMAL"].includes(field.logical_type)) return Number(raw);
  if (field.logical_type === "JSON") {
    try { return JSON.parse(raw); } catch { return raw; }
  }
  return raw;
}

export default function ManagedTableForm({ workspaceId, managedTables = [], onSubmit, onCancel, isSaving }) {
  const [name, setName] = useState("");
  const [fields, setFields] = useState([newField(0)]);
  const [foreignKeys, setForeignKeys] = useState([]);
  const [localError, setLocalError] = useState("");

  const fieldNames = useMemo(() => fields.map((item) => item.name).filter(Boolean), [fields]);

  function patchField(key, patch) {
    setFields((current) => current.map((item) => item.key === key ? { ...item, ...patch } : item));
  }

  function addField() {
    setFields((current) => [...current, newField(current.length)]);
  }

  function removeField(key) {
    setFields((current) => current.length === 1 ? current : current.filter((item) => item.key !== key));
    setForeignKeys((current) => current.filter((item) => !item.source_columns_text.split(",").map((value) => value.trim()).includes(fields.find((field) => field.key === key)?.name)));
  }

  function patchForeignKey(key, patch) {
    setForeignKeys((current) => current.map((item) => item.key === key ? { ...item, ...patch } : item));
  }

  function targetFields(tableId) {
    return managedTables.find((item) => item.id === tableId)?.fields || [];
  }

  async function submit(event) {
    event.preventDefault();
    setLocalError("");

    const cleanedFields = fields.map((field) => field.name.trim()).filter(Boolean);
    if (!name.trim() || cleanedFields.length !== fields.length) {
      setLocalError("La tabla y todos los campos deben tener un nombre.");
      return;
    }
    if (new Set(cleanedFields).size !== cleanedFields.length) {
      setLocalError("No puede haber nombres de campos duplicados.");
      return;
    }

    const payloadFields = fields.map((field) => {
      const payload = {
        name: field.name.trim(),
        logical_type: field.logical_type,
        nullable: Boolean(field.nullable),
        unique: Boolean(field.unique),
        is_identity: Boolean(field.is_identity),
      };
      if (field.logical_type === "STRING") payload.max_length = Number(field.max_length || 255);
      if (field.logical_type === "DECIMAL") {
        payload.numeric_precision = Number(field.numeric_precision || 18);
        payload.numeric_scale = Number(field.numeric_scale || 2);
      }
      const parsedDefault = parseDefault(field);
      if (field.has_default) payload.default = parsedDefault;
      return payload;
    });

    const fkPayload = foreignKeys.filter((fk) => fk.source_columns_text && fk.target_table_asset && fk.target_columns_text).map((fk) => ({
      columns: fk.source_columns_text.split(",").map((value) => value.trim()).filter(Boolean),
      target_table_asset: fk.target_table_asset,
      target_columns: fk.target_columns_text.split(",").map((value) => value.trim()).filter(Boolean),
      on_delete: fk.on_delete,
    }));
    const invalidFk = fkPayload.find((fk) => fk.columns.length !== fk.target_columns.length || fk.columns.some((column) => !fieldNames.includes(column)));
    if (invalidFk) {
      setLocalError("Cada FK debe tener la misma cantidad de columnas origen/destino y usar campos origen existentes.");
      return;
    }

    await onSubmit({
      workspace: workspaceId,
      name: normalizeTechnicalName(name),
      fields: payloadFields,
      primary_key: fields.filter((field) => field.is_primary_key).map((field) => field.name.trim()),
      foreign_keys: fkPayload,
    });
  }

  return <form className="formGrid" onSubmit={submit}>
    {localError && <div className="alert alert-error">{localError}</div>}
    <label className="field">Name<input value={name} onChange={(e) => setName(e.target.value)} placeholder="Orders" required /><small className="technicalNamePreview">Technical name: <strong>{normalizeTechnicalName(name)||"—"}</strong></small></label>

    <section className="subsectionCard">
      <div className="cardHeader responsiveCardHeader"><div><h3>Campos</h3><p className="mutedText">Define tipos, nulabilidad, unicidad, PK e identity.</p></div><button type="button" className="button secondaryButton smallButton" onClick={addField}>Agregar campo</button></div>
      <div className="tableWrap"><table className="dataTable"><thead><tr><th>Nombre</th><th>Tipo</th><th>Configuración</th><th>PK</th><th>Nullable</th><th>Unique</th><th>Default</th><th></th></tr></thead><tbody>{fields.map((field) => <tr key={field.key}>
        <td><input className="tableInput" value={field.name} onChange={(e) => patchField(field.key, { name: e.target.value })} placeholder="field_name" /></td>
        <td><select className="tableSelect" value={field.logical_type} onChange={(e) => patchField(field.key, { logical_type: e.target.value, is_identity: false })}>{LOGICAL_TYPES.map((type) => <option key={type}>{type}</option>)}</select></td>
        <td>{field.logical_type === "STRING" && <input className="miniInput" type="number" min="1" value={field.max_length} onChange={(e) => patchField(field.key, { max_length: e.target.value })} title="max_length" />}{field.logical_type === "DECIMAL" && <div className="miniInputGroup"><input className="miniInput" type="number" min="1" value={field.numeric_precision} onChange={(e) => patchField(field.key, { numeric_precision: e.target.value })} title="precision" /><input className="miniInput" type="number" min="0" value={field.numeric_scale} onChange={(e) => patchField(field.key, { numeric_scale: e.target.value })} title="scale" /></div>}{["INTEGER", "BIGINT"].includes(field.logical_type) && <label className="tinyCheck"><input type="checkbox" checked={field.is_identity} onChange={(e) => patchField(field.key, { is_identity: e.target.checked })} /> Identity</label>}</td>
        <td><input type="checkbox" checked={field.is_primary_key} onChange={(e) => patchField(field.key, { is_primary_key: e.target.checked, nullable: e.target.checked ? false : field.nullable })} /></td>
        <td><input type="checkbox" checked={field.nullable} disabled={field.is_primary_key} onChange={(e) => patchField(field.key, { nullable: e.target.checked })} /></td>
        <td><input type="checkbox" checked={field.unique} onChange={(e) => patchField(field.key, { unique: e.target.checked })} /></td>
        <td><div className="defaultEditor"><input type="checkbox" checked={field.has_default} onChange={(e) => patchField(field.key, { has_default: e.target.checked })} />{field.has_default && <input className="miniInput wideMiniInput" value={field.default} onChange={(e) => patchField(field.key, { default: e.target.value })} placeholder="valor" />}</div></td>
        <td><button type="button" className="button smallButton dangerButton" onClick={() => removeField(field.key)} disabled={fields.length === 1}>Quitar</button></td>
      </tr>)}</tbody></table></div>
    </section>

    <section className="subsectionCard">
      <div className="cardHeader responsiveCardHeader"><div><h3>Foreign Keys</h3><p className="mutedText">En esta fase las FK creadas por el builder apuntan a tablas MANAGED del mismo workspace.</p></div><button type="button" className="button secondaryButton smallButton" onClick={() => setForeignKeys((current) => [...current, newForeignKey(current.length)])} disabled={!managedTables.length}>Agregar FK</button></div>
      {!managedTables.length ? <p className="mutedText">Crea primero otra tabla MANAGED para poder referenciarla.</p> : foreignKeys.length === 0 ? <p className="mutedText">No hay relaciones nuevas definidas.</p> : <div className="tableWrap"><table className="dataTable"><thead><tr><th>Campo origen</th><th>Tabla destino</th><th>Campo destino</th><th>On delete</th><th></th></tr></thead><tbody>{foreignKeys.map((fk) => <tr key={fk.key}>
        <td><input className="tableInput" value={fk.source_columns_text} onChange={(e) => patchForeignKey(fk.key, { source_columns_text: e.target.value })} placeholder="customer_id o a,b" title={`Campos disponibles: ${fieldNames.join(", ")}`} /></td>
        <td><select className="tableSelect" value={fk.target_table_asset} onChange={(e) => patchForeignKey(fk.key, { target_table_asset: e.target.value, target_columns_text: "" })}><option value="">Seleccionar</option>{managedTables.map((table) => <option key={table.id} value={table.id}>{table.technical_name||table.table_name}</option>)}</select></td>
        <td><input className="tableInput" value={fk.target_columns_text} onChange={(e) => patchForeignKey(fk.key, { target_columns_text: e.target.value })} placeholder="id o a,b" title={`Campos disponibles: ${targetFields(fk.target_table_asset).map((field) => field.name).join(", ")}`} /></td>
        <td><select className="tableSelect" value={fk.on_delete} onChange={(e) => patchForeignKey(fk.key, { on_delete: e.target.value })}>{["NO ACTION", "RESTRICT", "CASCADE", "SET NULL"].map((value) => <option key={value}>{value}</option>)}</select></td>
        <td><button type="button" className="button smallButton dangerButton" onClick={() => setForeignKeys((current) => current.filter((item) => item.key !== fk.key))}>Quitar</button></td>
      </tr>)}</tbody></table></div>}
    </section>

    <div className="formActions"><button type="submit" className="button primaryButton" disabled={isSaving}>{isSaving ? "Creando..." : "Crear tabla"}</button><button type="button" className="button secondaryButton" onClick={onCancel}>Cancelar</button></div>
  </form>;
}
