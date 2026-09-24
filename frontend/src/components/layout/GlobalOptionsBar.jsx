"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import Icon from "@/components/ui/Icon";
import { useWorkspace } from "@/lib/hooks/useWorkspace";

const PLATFORM_ITEMS = [
  {label:"Sources",href:"/app/data-sources",icon:"databasePlus",roles:["OWNER","ADMIN","BUILDER"]},
  {label:"Structure",href:"/app/organizations",icon:"organization"},
  {label:"Governance",href:"/app/governance",icon:"shield",roles:["OWNER","ADMIN"]},
  {label:"Private connections",href:"/app/customer-gateway",icon:"gateway",roles:["OWNER","ADMIN"]},
  {label:"Python environments",href:"/app/environments",icon:"code"},
  {label:"Platform health",href:"/app/operations",icon:"pulse",roles:["OWNER","ADMIN"]},
  {label:"Import / Export",href:"/app/import-export",icon:"transfer",roles:["OWNER","ADMIN","BUILDER"]},
];

export default function GlobalOptionsBar(){
  const pathname=usePathname();
  const {activeWorkspace,organizations}=useWorkspace();
  const [open,setOpen]=useState(false); const ref=useRef(null);
  const org=organizations.find(x=>x.id===activeWorkspace?.organization); const role=org?.current_user_role;
  const items=PLATFORM_ITEMS.filter(item=>!item.roles||item.roles.includes(role));
  const active=items.some(item=>pathname===item.href||pathname.startsWith(`${item.href}/`));
  useEffect(()=>{const close=e=>{if(ref.current&&!ref.current.contains(e.target))setOpen(false)};document.addEventListener("pointerdown",close);return()=>document.removeEventListener("pointerdown",close)},[]);
  return <div className="globalOptionsBar" aria-label="Workspace options">
    <div className="globalOptionsLeft">
      <span className="globalOptionsLabel">Workspace</span>
      <span className="globalOptionsDivider"/>
      <div className="globalOptionsMenu" ref={ref}>
        <button type="button" className={`globalOptionsTrigger ${active?"active":""}`} onClick={()=>setOpen(v=>!v)} aria-expanded={open}>
          <Icon name="settings" size={15}/><span>Platform</span><Icon name="chevronDown" size={13}/>
        </button>
        {open&&<div className="globalOptionsDropdown">
          <div className="globalOptionsDropdownHead"><strong>Platform settings</strong><span>Workspace administration and runtime</span></div>
          <div className="globalOptionsGrid">{items.map(item=><Link key={item.href} href={item.href} onClick={()=>setOpen(false)} className={`globalOptionItem ${(pathname===item.href||pathname.startsWith(`${item.href}/`))?"active":""}`}><span className="globalOptionIcon"><Icon name={item.icon} size={17}/></span><span><strong>{item.label}</strong><small>{item.label==="Sources"?"Connections and data sources":item.label==="Structure"?"Organizations and workspaces":item.label==="Governance"?"Policies and access":item.label==="Private connections"?"Private network runtimes":item.label==="Python environments"?"Packages and compute":item.label==="Import / Export"?"Transfer history and data movement": "Runtime status and readiness"}</small></span></Link>)}</div>
        </div>}
      </div>
    </div>
    <div className="globalOptionsRight"><span className="globalWorkspaceName">{activeWorkspace?.name||"No workspace selected"}</span></div>
  </div>
}
