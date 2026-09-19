"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { label: "Transformations", href: "/app/transformations" },
  { label: "Lineage", href: "/app/dependencies" },
  { label: "Activity", href: "/app/executions" },
];

export default function PrepareTabs() {
  const pathname = usePathname();
  return (
    <nav className="prepareTabs" aria-label="Prepare">
      {TABS.map((tab) => {
        const active = pathname === tab.href || pathname.startsWith(`${tab.href}/`);
        return <Link key={tab.href} className={active ? "prepareTab active" : "prepareTab"} href={tab.href}>{tab.label}</Link>;
      })}
    </nav>
  );
}
