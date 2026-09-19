"use client";

import { useEffect, useMemo, useState } from "react";

const INITIAL_FORM = {
  organization: "",
  name: "",
  slug: "",
  description: "",
  status: "ACTIVE",
};

export default function WorkspaceForm({
  organizations,
  initialValue,
  onSubmit,
  onCancel,
  submitting,
}) {
  const writableOrganizations = useMemo(
    () =>
      organizations.filter((organization) =>
        ["OWNER", "ADMIN", "BUILDER"].includes(organization.current_user_role),
      ),
    [organizations],
  );

  const [form, setForm] = useState(INITIAL_FORM);

  useEffect(() => {
    if (initialValue) {
      setForm({
        organization: initialValue.organization || "",
        name: initialValue.name || "",
        slug: initialValue.slug || "",
        description: initialValue.description || "",
        status: initialValue.status || "ACTIVE",
      });
      return;
    }

    setForm({
      ...INITIAL_FORM,
      organization: writableOrganizations[0]?.id || "",
    });
  }, [initialValue, writableOrganizations]);

  function change(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    await onSubmit({
      organization: form.organization,
      name: form.name.trim(),
      slug: form.slug.trim(),
      description: form.description.trim(),
      status: form.status,
    });
  }

  if (!initialValue && writableOrganizations.length === 0) {
    return (
      <div className="emptyState compactEmptyState">
        <h3>No hay organizaciones editables</h3>
        <p>Necesitas rol OWNER, ADMIN o BUILDER para crear un workspace.</p>
      </div>
    );
  }

  return (
    <form className="inlineForm" onSubmit={submit}>
      <label className="field">
        Organización
        <select
          name="organization"
          value={form.organization}
          onChange={change}
          required
          disabled={Boolean(initialValue)}
        >
          {(initialValue ? organizations : writableOrganizations).map((organization) => (
            <option value={organization.id} key={organization.id}>
              {organization.name} ({organization.current_user_role || "-"})
            </option>
          ))}
        </select>
      </label>

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
            placeholder="workspace-principal"
            required
            maxLength={180}
          />
        </label>
      </div>

      <label className="field">
        Descripción
        <textarea name="description" value={form.description} onChange={change} rows={4} />
      </label>

      <label className="field">
        Estado
        <select name="status" value={form.status} onChange={change}>
          <option value="ACTIVE">Activo</option>
          <option value="ARCHIVED">Archivado</option>
        </select>
      </label>

      <div className="formActions">
        <button className="button buttonPrimary" type="submit" disabled={submitting}>
          {submitting ? "Guardando..." : initialValue ? "Guardar cambios" : "Crear workspace"}
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
