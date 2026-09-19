"use client";
import {useState} from "react";
import {PLATFORM_PACKAGES} from "@/lib/constants/pythonPackages";
export default function PackageLists({customerPackages=[],onRemove=null}){
 const [platformOpen,setPlatformOpen]=useState(true),[customerOpen,setCustomerOpen]=useState(true),[platformQuery,setPlatformQuery]=useState(""),[customerQuery,setCustomerQuery]=useState("");
 const pp=PLATFORM_PACKAGES.filter(([n])=>n.toLowerCase().includes(platformQuery.toLowerCase())); const cp=customerPackages.filter(x=>x.name.toLowerCase().includes(customerQuery.toLowerCase()));
 return <div className="packageLists">
  <section className="card environmentSection"><button className="packageSectionToggle" onClick={()=>setPlatformOpen(v=>!v)}><strong>Platform Packages</strong><span>Managed {platformOpen?"⌃":"⌄"}</span></button>{platformOpen&&<><input className="packageSearch" placeholder="Filter packages" value={platformQuery} onChange={e=>setPlatformQuery(e.target.value)}/><div className="packageListVertical">{pp.map(([name,version])=><div className="packageRow locked" key={name}><div><strong>{name}</strong><span>{version}</span></div><span className="packageLock">▣</span></div>)}</div></>}</section>
  <section className="card environmentSection"><button className="packageSectionToggle" onClick={()=>setCustomerOpen(v=>!v)}><strong>Customer Packages</strong><span>{customerPackages.length} {customerOpen?"⌃":"⌄"}</span></button>{customerOpen&&<><input className="packageSearch" placeholder="Filter packages" value={customerQuery} onChange={e=>setCustomerQuery(e.target.value)}/><div className="packageListVertical">{cp.map(x=><div className="packageRow" key={x.id}><div><strong>{x.name}</strong><span>{x.version_spec||"latest"}</span></div>{onRemove&&<button className="packageRemove" onClick={()=>onRemove(x.id)}>×</button>}</div>)}</div></>}</section>
 </div>
}
