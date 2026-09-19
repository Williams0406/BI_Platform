"use client";
import {useEffect,useState} from "react";
import {useParams} from "next/navigation";
import Spinner from "@/components/ui/Spinner";
import EmptyState from "@/components/ui/EmptyState";
import Alert from "@/components/ui/Alert";
import OptimizationReport from "@/components/ai/OptimizationReport";
import {useWorkspace} from "@/lib/hooks/useWorkspace";
import {getExecution} from "@/lib/services/executions";
import {getApiErrorMessage} from "@/lib/utils/errors";
import {getOptimizationModel,listOptimizationRuns,listOptimizationSolutions,optimizationConstraints,optimizationObjectives} from "@/lib/services/optimization";
const listValue=d=>Array.isArray(d)?d:d?.results||[];
export default function OptimizationDetail(){const {id}=useParams();const {activeWorkspace}=useWorkspace();const [model,setModel]=useState(null),[objective,setObjective]=useState(null),[constraints,setConstraints]=useState([]),[runs,setRuns]=useState([]),[solutions,setSolutions]=useState([]),[execution,setExecution]=useState(null),[loading,setLoading]=useState(true),[error,setError]=useState("");
async function load(){setLoading(true);setError("");try{const [m,o,c,r,s]=await Promise.all([getOptimizationModel(id),optimizationObjectives.list(),optimizationConstraints.list(),listOptimizationRuns({model:id}),listOptimizationSolutions()]);const rr=listValue(r);setModel(m);setObjective(listValue(o).find(x=>x.model===id)||m.objective||null);setConstraints(listValue(c).filter(x=>x.model===id&&x.enabled!==false));setRuns(rr);setSolutions(listValue(s).filter(x=>rr.some(q=>q.id===x.run)));const executionId=rr.find(x=>x.execution_id)?.execution_id;if(executionId){try{setExecution(await getExecution(executionId));}catch{setExecution(null);}}}catch(e){setError(getApiErrorMessage(e));}finally{setLoading(false);}}
useEffect(()=>{if(id&&activeWorkspace?.id)load();},[id,activeWorkspace?.id]);
useEffect(()=>{if(!execution?.id||!["QUEUED","RUNNING"].includes(execution.status))return;const t=setInterval(async()=>{try{const x=await getExecution(execution.id);setExecution(x);if(!["QUEUED","RUNNING"].includes(x.status))load();}catch{}},1500);return()=>clearInterval(t);},[execution?.id,execution?.status]);
if(loading)return <Spinner label="Loading Optimization report..."/>;if(!model)return <EmptyState title="Optimization report unavailable" description={error||"No optimization result was found."}/>;return <div className="pageStack reportPage">{error&&<Alert type="error">{error}</Alert>}<OptimizationReport model={model} objective={objective} constraints={constraints} runs={runs} solutions={solutions} execution={execution}/></div>}
