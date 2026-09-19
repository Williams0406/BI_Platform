"use client";
import {use,useEffect,useState} from "react";
import Spinner from "@/components/ui/Spinner";
import EmptyState from "@/components/ui/EmptyState";
import Alert from "@/components/ui/Alert";
import MLReport from "@/components/ai/MLReport";
import {useWorkspace} from "@/lib/hooks/useWorkspace";
import {getModel,listModelRuns,listModelVersions} from "@/lib/services/dataScience";
import {getExecution} from "@/lib/services/executions";
import {getApiErrorMessage} from "@/lib/utils/errors";
const listValue=d=>Array.isArray(d)?d:d?.results||[];
export default function ModelDetailPage({params}){const {id}=use(params);const {activeWorkspace}=useWorkspace();const [model,setModel]=useState(null),[runs,setRuns]=useState([]),[versions,setVersions]=useState([]),[execution,setExecution]=useState(null),[loading,setLoading]=useState(true),[error,setError]=useState("");
async function load(){setLoading(true);setError("");try{const [m,r,v]=await Promise.all([getModel(id),listModelRuns(id),listModelVersions(id)]);const rr=listValue(r);setModel(m);setRuns(rr);setVersions(listValue(v));const executionId=rr.find(x=>x.execution_id)?.execution_id;if(executionId){try{setExecution(await getExecution(executionId));}catch{setExecution(null);}}}catch(e){setError(getApiErrorMessage(e));}finally{setLoading(false);}}
useEffect(()=>{if(id&&activeWorkspace?.id)load();},[id,activeWorkspace?.id]);
useEffect(()=>{if(!execution?.id||!["QUEUED","RUNNING"].includes(execution.status))return;const t=setInterval(async()=>{try{const x=await getExecution(execution.id);setExecution(x);if(!["QUEUED","RUNNING"].includes(x.status))load();}catch{}},1500);return()=>clearInterval(t);},[execution?.id,execution?.status]);
if(loading)return <Spinner label="Loading Machine Learning report..."/>;if(!model)return <EmptyState title="Machine Learning report unavailable" description={error||"No model result was found."}/>;return <div className="pageStack reportPage">{error&&<Alert type="error">{error}</Alert>}<MLReport model={model} runs={runs} versions={versions} execution={execution}/></div>}
