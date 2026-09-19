"use client";

const OPS = ["eq", "ne", "gt", "gte", "lt", "lte", "contains", "in"];

export function normalizeAnalyticsFilters(filters) {
  return (filters || [])
    .filter((item) => item.field)
    .map((item) => ({
      ...item,
      value:
        item.operator === "in"
          ? String(item.value || "")
              .split(",")
              .map((value) => value.trim())
              .filter(Boolean)
          : item.value,
    }));
}

export default function AnalyticsFilterBuilder({ fields = [], filters = [], onChange }) {
  function add() {
    onChange([
      ...filters,
      { field: fields[0]?.name || "", operator: "eq", value: "" },
    ]);
  }

  function update(index, key, value) {
    onChange(filters.map((item, itemIndex) => (itemIndex === index ? { ...item, [key]: value } : item)));
  }

  function remove(index) {
    onChange(filters.filter((_, itemIndex) => itemIndex !== index));
  }

  return (
    <div className="analyticsFilters">
      <div className="queryToolbar">
        <button type="button" className="button secondaryButton" onClick={add} disabled={!fields.length}>
          Agregar filtro
        </button>
      </div>
      {filters.length > 0 && (
        <div className="filterRows">
          {filters.map((filter, index) => (
            <div className="filterRow" key={`${index}-${filter.field}`}>
              <select value={filter.field} onChange={(event) => update(index, "field", event.target.value)}>
                {fields.map((field) => (
                  <option key={field.id || field.name} value={field.name}>
                    {field.name}
                  </option>
                ))}
              </select>
              <select value={filter.operator} onChange={(event) => update(index, "operator", event.target.value)}>
                {OPS.map((operator) => (
                  <option key={operator} value={operator}>{operator}</option>
                ))}
              </select>
              <input
                value={filter.value ?? ""}
                onChange={(event) => update(index, "value", event.target.value)}
                placeholder={filter.operator === "in" ? "A, B, C" : "Valor"}
              />
              <button type="button" className="button dangerButton smallButton" onClick={() => remove(index)}>
                Quitar
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
