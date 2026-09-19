export function technicalTableName(table) {
  return String(table?.technical_name || table?.table_name || "").trim();
}

export function tableLabel(table) {
  return technicalTableName(table) || "Unnamed table";
}

export function normalizeTechnicalName(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^A-Za-z0-9_]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .toLowerCase()
    .slice(0, 63);
}
