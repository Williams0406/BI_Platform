"use client";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import Icon from "@/components/ui/Icon";
import { useWorkspace } from "@/lib/hooks/useWorkspace";
import { searchWorkspace } from "@/lib/services/globalSearch";

export default function GlobalSearch({ open, onClose }) {
  const { activeWorkspaceId } = useWorkspace();
  const [query, setQuery] = useState("");
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const dialogRef = useRef(null);
  const returnFocusRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    searchWorkspace(activeWorkspaceId, query).then(setItems).finally(() => setLoading(false));
  }, [open, activeWorkspaceId, query]);

  useEffect(() => {
    if (!open) return undefined;
    returnFocusRef.current = document.activeElement;
    const handler = (e) => {
      if (e.key === "Escape") { e.preventDefault(); onClose(); return; }
      if (e.key !== "Tab" || !dialogRef.current) return;
      const focusable = [...dialogRef.current.querySelectorAll('a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])')];
      if (!focusable.length) return;
      const first=focusable[0], last=focusable[focusable.length-1];
      if (e.shiftKey && document.activeElement===first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement===last) { e.preventDefault(); first.focus(); }
    };
    window.addEventListener("keydown", handler);
    return () => {
      window.removeEventListener("keydown", handler);
      returnFocusRef.current?.focus?.();
    };
  }, [open, onClose]);

  const grouped = useMemo(() => items.reduce((acc, x) => ((acc[x.type] ||= []).push(x), acc), {}), [items]);
  if (!open) return null;
  return <div className="commandOverlay" role="presentation" onMouseDown={onClose}>
    <section ref={dialogRef} className="commandPalette" role="dialog" aria-modal="true" aria-labelledby="global-search-title" onMouseDown={(e)=>e.stopPropagation()}>
      <h2 className="srOnly" id="global-search-title">Search workspace</h2>
      <div className="commandSearch"><Icon name="explore" size={18}/><label className="srOnly" htmlFor="global-search-input">Search workspace</label><input id="global-search-input" autoFocus value={query} onChange={(e)=>setQuery(e.target.value)} placeholder="Search dashboards, measures, tables and models…"/><kbd aria-hidden="true">Esc</kbd></div>
      <div className="commandResults" aria-live="polite" aria-busy={loading}>
        {loading ? <p className="commandEmpty">Searching workspace…</p> : null}
        {!loading && !items.length ? <p className="commandEmpty">No results found.</p> : null}
        {Object.entries(grouped).map(([type, list]) => <div className="commandGroup" key={type}><span>{type}</span>{list.slice(0,8).map((x)=><Link href={x.href} onClick={onClose} className="commandResult" key={x.id}><Icon name={x.icon} size={17}/><div><strong>{x.title}</strong><small>{x.subtitle || type}</small></div></Link>)}</div>)}
      </div>
    </section>
  </div>;
}
