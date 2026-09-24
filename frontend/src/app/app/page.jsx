"use client";
import Link from "next/link";
import {useEffect,useMemo,useState} from "react";
import Icon from "@/components/ui/Icon";
import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";
import Alert from "@/components/ui/Alert";
import {useWorkspace} from "@/lib/hooks/useWorkspace";
import {listDashboards,listReports} from "@/lib/services/analytics";
import {listViews} from "@/lib/services/views";
import {listComputeTargets,listEnvironments,deleteEnvironmentPackage} from "@/lib/services/environments";
import {getApiErrorMessage} from "@/lib/utils/errors";
import PackageLists from "@/components/environments/PackageLists";
function listValue(v){return Array.isArray(v)?v:v?.results||[]}
const OPERATION_TEMPLATES=[
 {type:"TABLE",icon:"table",name:"Table",description:"Editable operational grid"},
 {type:"SPREADSHEET",icon:"records",name:"Spreadsheet",description:"Dense editable data workspace"},
 {type:"FORM",icon:"report",name:"Form",description:"Record entry and editing"},
 {type:"KANBAN",icon:"view",name:"Kanban",description:"Cards grouped by status"},
 {type:"CALENDAR",icon:"activity",name:"Calendar",description:"Date-driven operational work"},
 {type:"MATRIX",icon:"dashboard",name:"Matrix",description:"Cross-tab operational layout"},
];
export default function OverviewPage(){
 const {activeWorkspace}=useWorkspace();const [dashboards,setDashboards]=useState([]);const [reports,setReports]=useState([]);const [operationalViews,setOperationalViews]=useState([]);const [loading,setLoading]=useState(true);const [error,setError]=useState("");const [runtimeOpen,setRuntimeOpen]=useState(false);const [customerPackages,setCustomerPackages]=useState([]);
 useEffect(()=>{if(!activeWorkspace?.id){setLoading(false);return;}let live=true;setLoading(true);Promise.all([listDashboards(activeWorkspace.id),listReports(activeWorkspace.id),listViews({workspace:activeWorkspace.id})]).then(([d,r,v])=>{if(!live)return;setDashboards(listValue(d).filter(x=>x?.layout?.workspace_state!=="DRAFT"));setReports(listValue(r));setOperationalViews(listValue(v).filter(x=>x.status==="ACTIVE"));}).catch(e=>live&&setError(getApiErrorMessage(e))).finally(()=>live&&setLoading(false));return()=>{live=false}},[activeWorkspace?.id]);
 async function openRuntime(){setRuntimeOpen(true);try{const [tr,er]=await Promise.all([listComputeTargets(activeWorkspace.id),listEnvironments(activeWorkspace.id)]);const target=listValue(tr).find(x=>x.kind==="CUSTOMER");const env=listValue(er).find(x=>x.compute_target===target?.id||x.compute_target?.id===target?.id);setCustomerPackages(env?.packages||[])}catch{setCustomerPackages([])}}
 const modules=useMemo(()=>[...dashboards.map(x=>({...x,kind:"Dashboard",icon:"dashboard",href:`/app/dashboards/${x.id}`})),...reports.map(x=>({...x,kind:"Report",icon:"report",href:`/app/reports/${x.id}`})),...operationalViews.map(x=>({...x,kind:"Operation",icon:"view",href:`/app/views/${x.id}`,description:x.description||`${x.view_type} operational template`}))],[dashboards,reports,operationalViews]);
 if(!activeWorkspace)return <EmptyState title="Select a workspace" description="Overview shows published workspace content."/>;
 return <div className="pageStack overviewPage"><header className="pageHeader pageHeaderActions"><div><p className="eyebrow">{activeWorkspace.name}</p><h1>Overview</h1></div><div className="headerActions homeQuickActions"><button className="homeQuickAction" onClick={openRuntime}><span className="homeQuickIcon"><Icon name="python" size={17}/></span><span><strong>Python packages</strong><small>Runtime & libraries</small></span></button><Link className="homeQuickAction" href="/app/data-model"><span className="homeQuickIcon"><Icon name="model" size={17}/></span><span><strong>Open data</strong><small>Model & prepare</small></span></Link><Link className="homeQuickAction primary" href="/app/analytics"><span className="homeQuickIcon"><Icon name="plus" size={17}/></span><span><strong>Build</strong><small>Report or dashboard</small></span></Link></div></header>{error&&<Alert type="error">{error}</Alert>}{loading?<Spinner label="Loading overview..."/>:modules.length===0?<EmptyState title="Nothing published yet" description="" actionHref="/app/analytics" actionLabel="Open analytics"/>:<section className="overviewModuleGrid">{modules.map(item=><Link href={item.href} className="overviewModule" key={`${item.kind}-${item.id}`}><div className="overviewModulePreview"><Icon name={item.icon} size={34}/><span>{item.kind}</span></div><div className="overviewModuleBody"><div><strong>{item.name}</strong><p>{item.description||`${item.kind} in ${activeWorkspace.name}`}</p></div><span className="overviewOpen">Open ↗</span></div></Link>)}</section>}
 <section className="homeOperationalTemplates"><div className="homeSectionHeading"><div><span>OPERATIONS</span><h2>Operational templates</h2></div><Link href="/app/views">View all →</Link></div><div className="homeTemplateGrid">{OPERATION_TEMPLATES.map(template=><Link key={template.type} href={`/app/views?template=${template.type}`} className="homeTemplateCard"><span className="homeTemplateIcon"><Icon name={template.icon} size={19}/></span><strong>{template.name}</strong><small>{template.description}</small></Link>)}</div></section>
 {runtimeOpen&&<div className="modalBackdrop" onMouseDown={e=>{if(e.target===e.currentTarget)setRuntimeOpen(false)}}><section className="runtimePackagesModal"><div className="packageExplorerHeader"><h2>Python packages</h2><button className="packageRemove" onClick={()=>setRuntimeOpen(false)}>×</button></div><PackageLists customerPackages={customerPackages} onRemove={async id=>{await deleteEnvironmentPackage(id);await openRuntime()}}/><div className="formActions"><Link className="button secondaryButton" href="/app/environments" onClick={()=>setRuntimeOpen(false)}>Python environments</Link><Link className="button primaryButton" href="/app/environments/packages" onClick={()=>setRuntimeOpen(false)}>Explore packages</Link></div></section></div>}
 </div>
}
