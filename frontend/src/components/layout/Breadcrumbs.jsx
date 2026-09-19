"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { getNavigationGroupForPath } from "@/lib/constants/navigation";

function prettify(segment) {
  return decodeURIComponent(segment)
    .replace(/-/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export default function Breadcrumbs() {
  const pathname = usePathname();
  if (pathname === "/app") return <span className="breadcrumbCurrent">Home</span>;

  const group = getNavigationGroupForPath(pathname);
  const activeItem = group?.items?.find(
    (item) => pathname === item.href || pathname.startsWith(`${item.href}/`),
  );
  const extraSegments = activeItem
    ? pathname.slice(activeItem.href.length).split("/").filter(Boolean)
    : [];

  return (
    <nav className="breadcrumbs" aria-label="Breadcrumb">
      <Link href="/app">Home</Link>
      {group ? (
        <>
          <span className="breadcrumbSeparator">/</span>
          <span>{group.label}</span>
        </>
      ) : null}
      {activeItem ? (
        <>
          <span className="breadcrumbSeparator">/</span>
          <Link href={activeItem.href}>{activeItem.label}</Link>
        </>
      ) : null}
      {extraSegments.map((segment, index) => (
        <span className="breadcrumbTail" key={`${segment}-${index}`}>
          <span className="breadcrumbSeparator">/</span>
          <span className="breadcrumbCurrent">{prettify(segment)}</span>
        </span>
      ))}
    </nav>
  );
}
