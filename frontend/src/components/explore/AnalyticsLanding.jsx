"use client";
import Link from "next/link";
import {useEffect,useState} from "react";
import WorkspaceCommandBar from "@/components/data/WorkspaceCommandBar";
import Icon from "@/components/ui/Icon";
import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";
import Alert from "@/components/ui/Alert";
import {useWorkspace} from "@/lib/hooks/useWorkspace";
import {deleteChart,deleteDashboard,listCharts,listDashboards} from "@/lib/services/analytics";
import {getApiErrorMessage} from "@/lib/utils/errors";
const list=v=>Array.isArray(v)?v:v?.results||[];
export default function AnalyticsLanding(){
 const {activeWorkspace}=useWorkspace();
 const [charts,setCharts]=useState([]),[dashboards,setDashboards]=useState([]),[loading,setLoading]=useState(true),[error,setError]=useState("");
 async function load(){if(!activeWorkspace?.id){setLoading(false);return}setLoading(true);setError("");try{const [c,d]=await Promise.all([listCharts(activeWorkspace.id),listDashboards(activeWorkspace.id)]);setCharts(list(c));setDashboards(list(d).filter(x=>x?.layout?.workspace_state!=="DRAFT"))}catch(e){setError(getApiErrorMessage(e))}finally{setLoading(false)}}
 useEffect(()=>{load()},[activeWorkspace?.id]);
 async function remove(kind,item,e){e.preventDefault();e.stopPropagation();if(!window.confirm(`Delete "${item.name}"?`))return;try{kind==="dashboard"?await deleteDashboard(item.id):await deleteChart(item.id);await load()}catch(err){setError(getApiErrorMessage(err))}}
 if(!activeWorkspace)return <EmptyState title="Select a workspace" description="Analytics belongs to the active workspace."/>;
 return <div className="analyticsLandingPage">
  <WorkspaceCommandBar view="analytics"><Link href="/app/analytics/new" className="modelIconAction" title="New analytics workspace" aria-label="New analytics workspace"><Icon name="plus" size={17}/></Link></WorkspaceCommandBar>
  <div className="analyticsLandingBody">{error&&<Alert type="error">{error}</Alert>}{loading?<Spinner label="Loading analytics…"/>:<div className="ovViewGrid analyticsSimpleGrid workspaceLibraryGrid">
   {dashboards.map(x=><Link className="ovViewCard ovViewCardClickable analyticsSimpleCard workspaceLibraryCard" href={`/app/dashboards/${x.id}`} key={`d-${x.id}`}><div className="ovViewCardCopy"><small>DASHBOARD</small><h3>{x.name}</h3></div><button type="button" className="ovIconButton danger ovCardDelete" title="Delete dashboard" aria-label={`Delete ${x.name}`} onClick={e=>remove("dashboard",x,e)}>×</button></Link>)}
   {charts.map(x=><Link className="ovViewCard ovViewCardClickable analyticsSimpleCard workspaceLibraryCard" href={`/app/analytics/${x.id}`} key={`c-${x.id}`}><div className="ovViewCardCopy"><small>REPORT</small><h3>{x.name}</h3></div><button type="button" className="ovIconButton danger ovCardDelete" title="Delete report" aria-label={`Delete ${x.name}`} onClick={e=>remove("report",x,e)}>×</button></Link>)}
   {!charts.length&&!dashboards.length?<EmptyState title="No analytics yet" description="Use + to create a blank analytical workspace."/>:null}
  </div>}</div>
 </div>
}
