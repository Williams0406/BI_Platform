export const NAVIGATION_SECTIONS = [
  { id: "overview", label: "Home", icon: "home", href: "/app" },
  { id: "data", label: "Data", icon: "database", href: "/app/data-model" },
  { id: "table-workspace", label: "Table", icon: "table", href: "/app/data-table" },
  { id: "dashboards", label: "Analytics", icon: "dashboard", href: "/app/dashboards" },
  { id: "scripts", label: "Code", icon: "code", href: "/app/scripts" },
  { id: "views", label: "Operations", icon: "view", href: "/app/views" },
  { id: "advanced", label: "Intelligence", icon: "sparkles", items: [
    { label: "Machine learning", href: "/app/data-science", icon: "brain" },
    { label: "Optimization", href: "/app/optimization", icon: "optimize" },
  ]},
  { id: "manage", label: "Administration", icon: "settings", items: [
    { label: "Sources", href: "/app/data-sources", icon: "database" },
    { label: "Structure", href: "/app/organizations", icon: "organization" },
    { label: "Governance", href: "/app/governance", icon: "shield" },
    { label: "Private connections", href: "/app/customer-gateway", icon: "gateway" },
    { label: "Python environments", href: "/app/environments", icon: "code" },
    { label: "Platform health", href: "/app/operations", icon: "pulse" },
    { label: "Import / Export", href: "/app/import-export", icon: "transfer" },
  ]},
];
export function isNavigationItemActive(pathname, href) {
  if (!href) return false;
  if (href === "/app") return pathname === "/app";
  if (href === "/app/data-model") return pathname === "/app/data-model" || pathname.startsWith("/app/data-model/") || pathname.startsWith("/app/data-assets");
  if (href === "/app/data-table") return pathname === "/app/data-table" || pathname.startsWith("/app/transformations") || pathname.startsWith("/app/dependencies") || pathname.startsWith("/app/executions") || pathname.startsWith("/app/metrics");
  if (href === "/app/dashboards") return ["/app/dashboards","/app/analytics","/app/reports"].some((p)=>pathname===p||pathname.startsWith(`${p}/`));
  return pathname === href || pathname.startsWith(`${href}/`);
}
export function getNavigationGroupForPath(pathname) { return NAVIGATION_SECTIONS.find((section) => section.items?.some((item) => isNavigationItemActive(pathname, item.href))); }
