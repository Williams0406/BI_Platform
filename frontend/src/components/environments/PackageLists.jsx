"use client";
import {useMemo,useState} from "react";
import {PLATFORM_PACKAGES} from "@/lib/constants/pythonPackages";

const norm=v=>(v||"").toLowerCase().replace(/[-_.]+/g,"-");
export default function PackageLists({customerPackages=[],onRemove=null,compact=false}){
 const [query,setQuery]=useState(""),[logId,setLogId]=useState(null);
 const rows=useMemo(()=>{
  const platform=PLATFORM_PACKAGES.map(([name,version])=>({key:`platform-${name}`,name,version,origin:"Platform",status:"MANAGED",locked:true}));
  const platformNames=new Set(platform.map(x=>norm(x.name)));
  const customer=customerPackages.map(x=>({key:x.id,name:x.name,version:x.installed_version||x.version_spec||"latest",origin:platformNames.has(norm(x.name))?"Environment":"Customer",status:x.status,locked:false,raw:x}));
  const q=query.trim().toLowerCase();
  return [...platform,...customer].filter(x=>!q||x.name.toLowerCase().includes(q)||x.origin.toLowerCase().includes(q)||x.status.toLowerCase().includes(q));
 },[customerPackages,query]);
 return <section className={`card unifiedPackageSection ${compact?"compact":""}`}>
  <div className="unifiedPackageHeader"><div><strong>Python packages</strong><span>{PLATFORM_PACKAGES.length} platform · {customerPackages.length} environment/customer</span></div></div>
  <input className="packageSearch unifiedPackageSearch" placeholder="Filter packages by name, source or status" value={query} onChange={e=>setQuery(e.target.value)}/>
  <div className="unifiedPackageList">
   <div className="unifiedPackageColumns"><span>Package</span><span>Source</span><span>Version</span><span>Status</span><span></span></div>
   {rows.map(x=><div key={x.key} className="unifiedPackageEntry">
    <div className="unifiedPackageRow"><strong>{x.name}</strong><span className={`packageOriginBadge ${x.origin.toLowerCase()}`}>{x.origin}</span><span>{x.version}</span><span className={`packageStatus ${x.status.toLowerCase()}`}>{x.status}</span><div className="packageRowActions">{x.raw?.log&&<button className="packageLogButton" onClick={()=>setLogId(logId===x.key?null:x.key)}>Log</button>}{onRemove&&!x.locked&&<button className="packageRemove" disabled={x.status==="UNINSTALLING"} title="Remove package" onClick={()=>onRemove(x.raw.id)}>×</button>}</div></div>
    {logId===x.key&&<pre className="packageInstallLog">{x.raw.log}</pre>}
   </div>)}
   {!rows.length&&<div className="packageEmpty">No packages match this filter.</div>}
  </div>
 </section>
}
