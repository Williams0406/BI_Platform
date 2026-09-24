"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { label: "Table", href: "/app/data-table" },
  { label: "Code", href: "/app/scripts" },
];

export default function PrepareTabs() {
  const pathname = usePathname();
  return <nav className="prepareTabs" aria-label="Prepare">{TABS.map((tab) => {
    const active = pathname === tab.href || pathname.startsWith(`${tab.href}/`);
    return <Link key={tab.href} className={active ? "prepareTab active" : "prepareTab"} href={tab.href}>{tab.label}</Link>;
  })}</nav>;
}
