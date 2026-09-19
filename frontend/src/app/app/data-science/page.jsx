"use client";
import Link from "next/link";
import {useEffect,useMemo,useState} from "react";
import Alert from "@/components/ui/Alert";
import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";
import {useWorkspace} from "@/lib/hooks/useWorkspace";
import {listModels,listModelRuns,listModelVersions} from "@/lib/services/dataScience";
import {getApiErrorMessage} from "@/lib/utils/errors";
const listValue=d=>Array.isArray(d)?d:d?.results||[];
export default function DataSciencePage(){const {activeWorkspace}=useWorkspace();const [models,setModels]=useState([]),[runs,setRuns]=useState([]),[versions,setVersions]=useState([]),[loading,setLoading]=useState(true),[error,setError]=useState("");
useEffect(()=>{async function load(){if(!activeWorkspace?.id){setLoading(false);return;}setLoading(true);try{const [m,r,v]=await Promise.all([listModels(activeWorkspace.id),listModelRuns(),listModelVersions()]);setModels(listValue(m));setRuns(listValue(r));setVersions(listValue(v));}catch(e){setError(getApiErrorMessage(e));}finally{setLoading(false);}}load();},[activeWorkspace?.id]);
const rows=useMemo(()=>models.map(m=>{const mr=runs.filter(r=>r.model===m.id).sort((a,b)=>new Date(b.created_at)-new Date(a.created_at));return {...m,latest:mr[0],runCount:mr.length,versionCount:versions.filter(v=>v.model===m.id).length};}),[models,runs,versions]);
if(!activeWorkspace)return <EmptyState title="Select a workspace" description="Machine Learning reports are scoped to the active workspace."/>;if(loading)return <Spinner label="Loading Machine Learning reports..."/>;return <div className="pageStack reportIndex"><header className="pageHeader"><div><p className="eyebrow">AI & Optimization</p><h1>Machine Learning</h1><p>Reports generated automatically from Machine Learning executions created in code blocks.</p></div></header>{error&&<Alert type="error">{error}</Alert>}{rows.length?<div className="reportIndexTable"><div className="reportIndexHead"><span>Model</span><span>Type</span><span>Algorithm</span><span>Latest status</span><span>Runs</span><span>Versions</span></div>{rows.map(x=><Link href={`/app/data-science/models/${x.id}`} className="reportIndexRow" key={x.id}><strong>{x.name}</strong><span>{x.task_type?.replaceAll("_"," ")}</span><span>{x.algorithm?.replaceAll("_"," ")}</span><span>{x.latest?.status||"NOT RUN"}</span><span>{x.runCount}</span><span>{x.versionCount}</span></Link>)}</div>:<EmptyState title="No Machine Learning reports" description="When a code-block execution produces an ML model/run, its report will appear here."/>}</div>}
