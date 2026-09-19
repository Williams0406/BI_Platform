"use client";
import Link from "next/link";
import {useEffect,useMemo,useState} from "react";
import Icon from "@/components/ui/Icon";
import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";
import Alert from "@/components/ui/Alert";
import {useWorkspace} from "@/lib/hooks/useWorkspace";
import {listDashboards,listReports} from "@/lib/services/analytics";
import {listComputeTargets,listEnvironments,deleteEnvironmentPackage} from "@/lib/services/environments";
import {getApiErrorMessage} from "@/lib/utils/errors";
import PackageLists from "@/components/environments/PackageLists";
function listValue(v){return Array.isArray(v)?v:v?.results||[]}
export default function OverviewPage(){
 const {activeWorkspace}=useWorkspace();const [dashboards,setDashboards]=useState([]);const [reports,setReports]=useState([]);const [loading,setLoading]=useState(true);const [error,setError]=useState("");const [runtimeOpen,setRuntimeOpen]=useState(false);const [customerPackages,setCustomerPackages]=useState([]);
 useEffect(()=>{if(!activeWorkspace?.id){setLoading(false);return;}let live=true;setLoading(true);Promise.all([listDashboards(activeWorkspace.id),listReports(activeWorkspace.id)]).then(([d,r])=>{if(!live)return;setDashboards(listValue(d).filter(x=>x?.layout?.workspace_state!=="DRAFT"));setReports(listValue(r));}).catch(e=>live&&setError(getApiErrorMessage(e))).finally(()=>live&&setLoading(false));return()=>{live=false}},[activeWorkspace?.id]);
 async function openRuntime(){setRuntimeOpen(true);try{const [tr,er]=await Promise.all([listComputeTargets(activeWorkspace.id),listEnvironments(activeWorkspace.id)]);const target=listValue(tr).find(x=>x.kind==="CUSTOMER");const env=listValue(er).find(x=>x.compute_target===target?.id||x.compute_target?.id===target?.id);setCustomerPackages(env?.packages||[])}catch{setCustomerPackages([])}}
 const modules=useMemo(()=>[...dashboards.map(x=>({...x,kind:"Dashboard",icon:"dashboard",href:`/app/dashboards/${x.id}?fullscreen=1`})),...reports.map(x=>({...x,kind:"Report",icon:"report",href:`/app/reports/${x.id}?fullscreen=1`}))],[dashboards,reports]);
 if(!activeWorkspace)return <EmptyState title="Select a workspace" description="Overview shows published workspace content."/>;
 return <div className="pageStack overviewPage"><header className="pageHeader pageHeaderActions"><div><p className="eyebrow">{activeWorkspace.name}</p><h1>Overview</h1></div><div className="headerActions"><button className="button secondaryButton" onClick={openRuntime}>Python packages</button><Link className="button secondaryButton" href="/app/data-model">Open data</Link><Link className="button primaryButton" href="/app/dashboards">Build</Link></div></header>{error&&<Alert type="error">{error}</Alert>}{loading?<Spinner label="Loading overview..."/>:modules.length===0?<EmptyState title="Nothing published yet" description="" actionHref="/app/dashboards" actionLabel="Open dashboard studio"/>:<section className="overviewModuleGrid">{modules.map(item=><Link href={item.href} className="overviewModule" key={`${item.kind}-${item.id}`}><div className="overviewModulePreview"><Icon name={item.icon} size={34}/><span>{item.kind}</span></div><div className="overviewModuleBody"><div><strong>{item.name}</strong><p>{item.description||`${item.kind} in ${activeWorkspace.name}`}</p></div><span className="overviewOpen">Open ↗</span></div></Link>)}</section>}
 {runtimeOpen&&<div className="modalBackdrop" onMouseDown={e=>{if(e.target===e.currentTarget)setRuntimeOpen(false)}}><section className="runtimePackagesModal"><div className="packageExplorerHeader"><h2>Python packages</h2><button className="packageRemove" onClick={()=>setRuntimeOpen(false)}>×</button></div><PackageLists customerPackages={customerPackages} onRemove={async id=>{await deleteEnvironmentPackage(id);await openRuntime()}}/><div className="formActions"><Link className="button secondaryButton" href="/app/environments" onClick={()=>setRuntimeOpen(false)}>Python environments</Link><Link className="button primaryButton" href="/app/environments/packages" onClick={()=>setRuntimeOpen(false)}>Explore packages</Link></div></section></div>}
 </div>
}
