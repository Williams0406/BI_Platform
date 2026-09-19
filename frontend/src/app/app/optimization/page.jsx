"use client";
import Link from "next/link";
import {useEffect,useMemo,useState} from "react";
import Alert from "@/components/ui/Alert";
import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";
import {useWorkspace} from "@/lib/hooks/useWorkspace";
import {listOptimizationModels,listOptimizationRuns} from "@/lib/services/optimization";
import {getApiErrorMessage} from "@/lib/utils/errors";
const listValue=d=>Array.isArray(d)?d:d?.results||[];
export default function OptimizationPage(){const {activeWorkspace}=useWorkspace();const [models,setModels]=useState([]),[runs,setRuns]=useState([]),[loading,setLoading]=useState(true),[error,setError]=useState("");
useEffect(()=>{async function load(){if(!activeWorkspace?.id){setLoading(false);return;}setLoading(true);try{const [m,r]=await Promise.all([listOptimizationModels(activeWorkspace.id),listOptimizationRuns()]);setModels(listValue(m));setRuns(listValue(r));}catch(e){setError(getApiErrorMessage(e));}finally{setLoading(false);}}load();},[activeWorkspace?.id]);
const rows=useMemo(()=>models.map(m=>{const mr=runs.filter(r=>r.model===m.id).sort((a,b)=>new Date(b.created_at)-new Date(a.created_at));return {...m,latest:mr[0],runCount:mr.length};}),[models,runs]);
if(!activeWorkspace)return <EmptyState title="Select a workspace" description="Optimization reports are scoped to the active workspace."/>;if(loading)return <Spinner label="Loading Optimization reports..."/>;return <div className="pageStack reportIndex"><header className="pageHeader"><div><p className="eyebrow">AI & Optimization</p><h1>Optimization</h1><p>Reports generated automatically from optimization models solved in code blocks.</p></div></header>{error&&<Alert type="error">{error}</Alert>}{rows.length?<div className="reportIndexTable"><div className="reportIndexHead"><span>Model</span><span>Problem</span><span>Latest status</span><span>Objective</span><span>Gap</span><span>Runs</span></div>{rows.map(x=><Link href={`/app/optimization/${x.id}`} className="reportIndexRow" key={x.id}><strong>{x.name}</strong><span>{x.problem_type}</span><span>{x.latest?.status||"NOT RUN"}</span><span>{x.latest?.objective_value??"—"}</span><span>{x.latest?.gap??"—"}</span><span>{x.runCount}</span></Link>)}</div>:<EmptyState title="No Optimization reports" description="When a code-block execution produces an optimization model/run, its report will appear here."/>}</div>}
