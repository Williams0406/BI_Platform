"use client";

import { useEffect, useState } from "react";

const INITIAL_FORM = {
  name: "",
  slug: "",
  status: "ACTIVE",
};

export default function OrganizationForm({ initialValue, onSubmit, onCancel, submitting }) {
  const [form, setForm] = useState(INITIAL_FORM);

  useEffect(() => {
    if (initialValue) {
      setForm({
        name: initialValue.name || "",
        slug: initialValue.slug || "",
        status: initialValue.status || "ACTIVE",
      });
    } else {
      setForm(INITIAL_FORM);
    }
  }, [initialValue]);

  function change(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    await onSubmit({
      name: form.name.trim(),
      slug: form.slug.trim(),
      status: form.status,
    });
  }

  return (
    <form className="inlineForm" onSubmit={submit}>
      <div className="fieldGrid">
        <label className="field">
          Nombre
          <input name="name" value={form.name} onChange={change} required maxLength={180} />
        </label>
        <label className="field">
          Slug
          <input
            name="slug"
            value={form.slug}
            onChange={change}
            placeholder="empresa-demo"
            required
            maxLength={180}
          />
        </label>
      </div>

      <label className="field">
        Estado
        <select name="status" value={form.status} onChange={change}>
          <option value="ACTIVE">Activa</option>
          <option value="SUSPENDED">Suspendida</option>
          <option value="ARCHIVED">Archivada</option>
        </select>
      </label>

      <div className="formActions">
        <button className="button buttonPrimary" type="submit" disabled={submitting}>
          {submitting ? "Guardando..." : initialValue ? "Guardar cambios" : "Crear organización"}
        </button>
        {onCancel ? (
          <button className="button buttonGhost" type="button" onClick={onCancel} disabled={submitting}>
            Cancelar
          </button>
        ) : null}
      </div>
    </form>
  );
}
