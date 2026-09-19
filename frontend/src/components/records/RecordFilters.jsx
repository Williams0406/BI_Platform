"use client";

const OPERATORS = [
  ["eq", "="], ["ne", "≠"], ["gt", ">"], ["gte", "≥"], ["lt", "<"], ["lte", "≤"], ["contains", "Contiene"],
];

export default function RecordFilters({ fields, filters, setFilters, onApply, onClear }) {
  function addFilter() {
    setFilters((current) => [...current, { id: `${Date.now()}-${current.length}`, field: fields[0]?.name || "", operator: "eq", value: "" }]);
  }
  function patch(id, patch) { setFilters((current) => current.map((item) => item.id === id ? { ...item, ...patch } : item)); }
  return <div className="filterBuilder">
    <div className="cardHeader responsiveCardHeader"><div><h3>Filtros</h3><p className="mutedText">Operadores soportados por el Records Engine.</p></div><button type="button" className="button secondaryButton smallButton" onClick={addFilter}>Agregar filtro</button></div>
    {filters.map((filter) => <div className="filterRow" key={filter.id}><select value={filter.field} onChange={(e) => patch(filter.id, { field: e.target.value })}>{fields.map((field) => <option key={field.id} value={field.name}>{field.name}</option>)}</select><select value={filter.operator} onChange={(e) => patch(filter.id, { operator: e.target.value })}>{OPERATORS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><input value={filter.value} onChange={(e) => patch(filter.id, { value: e.target.value })} placeholder="valor" /><button className="button smallButton dangerButton" type="button" onClick={() => setFilters((current) => current.filter((item) => item.id !== filter.id))}>Quitar</button></div>)}
    <div className="formActions"><button type="button" className="button primaryButton smallButton" onClick={onApply}>Aplicar</button><button type="button" className="button secondaryButton smallButton" onClick={onClear}>Limpiar</button></div>
  </div>;
}
