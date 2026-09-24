"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { listCharts, listDashboards } from "@/lib/services/analytics";
import { listDataAssets, listDataSources } from "@/lib/services/dataSources";
import { listMetrics } from "@/lib/services/metrics";
import { listTransformations } from "@/lib/services/transformations";

const BUILD_ROLES = ["OWNER", "ADMIN", "BUILDER"];
const listValue = (data) => Array.isArray(data) ? data : data?.results || [];

function hiddenKey(workspaceId) { return `bi:onboarding-hidden:${workspaceId}`; }

export function useWorkspaceSetup(activeWorkspaceId) {
  const [state,setState]=useState({
    loading:true,error:"",
    sources:[],assets:[],transformations:[],metrics:[],charts:[],dashboards:[],
  });
  useEffect(()=>{
    let alive=true;
    if(!activeWorkspaceId){setState(s=>({...s,loading:false}));return;}
    setState(s=>({...s,loading:true,error:""}));
    Promise.allSettled([
      listDataSources(activeWorkspaceId),
      listDataAssets(activeWorkspaceId),
      listTransformations(activeWorkspaceId),
      listMetrics(activeWorkspaceId),
      listCharts(activeWorkspaceId),
      listDashboards(activeWorkspaceId),
    ]).then(results=>{
      if(!alive)return;
      const values=results.map(x=>x.status==="fulfilled"?listValue(x.value):[]);
      const failed=results.some(x=>x.status==="rejected");
      setState({
        loading:false,
        error:failed?"Some setup signals could not be loaded. Progress below only uses confirmed data.":"",
        sources:values[0],assets:values[1],transformations:values[2],metrics:values[3],charts:values[4],dashboards:values[5],
      });
    });
    return()=>{alive=false;};
  },[activeWorkspaceId]);
  return state;
}

export function buildSetupSteps(state) {
  const source=state.sources[0];
  return [
    {
      id:"source",label:"Connect data",description:"Register a managed, external or private source.",
      complete:state.sources.length>0,required:true,
      href:"/app/data-sources",action:state.sources.length?"Review sources":"Connect a source",
    },
    {
      id:"catalog",label:"Bring data into the Catalog",description:"Sync or create governed assets that the rest of the platform can use.",
      complete:state.assets.length>0,required:true,
      href:source?`/app/data-sources/${source.id}`:"/app/data-sources",action:state.assets.length?"Browse catalog":"Sync source catalog",
      completeHref:"/app/data-assets",
    },
    {
      id:"prepare",label:"Prepare data",description:"Optional: transform raw inputs when analysis needs a reusable derived dataset.",
      complete:state.transformations.length>0,required:false,
      href:"/app/scripts",action:state.transformations.length?"Open Code":"Prepare data in Code (optional)",
    },
    {
      id:"metric",label:"Define business meaning",description:"Create a semantic model and reusable measure for visual analysis.",
      complete:state.metrics.length>0,required:true,
      href:"/app/scripts",action:state.metrics.length?"Open Code":"Define a measure in Code",
    },
    {
      id:"analysis",label:"Save an analysis",description:"Use Explore to answer a question and save the useful visual.",
      complete:state.charts.length>0,required:true,
      href:"/app/analytics",action:state.charts.length?"Open Explore":"Create an analysis",
    },
    {
      id:"dashboard",label:"Build a dashboard",description:"Compose saved analyses into a decision view for other users.",
      complete:state.dashboards.length>0,required:true,
      href:"/app/analytics",action:state.dashboards.length?"Open analytics":"Build a dashboard",
    },
  ];
}

export default function WorkspaceSetupGuide({
  activeWorkspace,
  role,
  variant="compact",
  onHidden,
}) {
  const state=useWorkspaceSetup(activeWorkspace?.id);
  const [hidden,setHidden]=useState(false);
  const canBuild=BUILD_ROLES.includes(role);
  const steps=useMemo(()=>buildSetupSteps(state),[state]);
  const required=steps.filter(x=>x.required);
  const completed=required.filter(x=>x.complete).length;
  const done=required.length>0&&completed===required.length;
  const progress=required.length?Math.round(completed/required.length*100):0;

  useEffect(()=>{
    if(!activeWorkspace?.id||typeof window==="undefined")return;
    setHidden(window.localStorage.getItem(hiddenKey(activeWorkspace.id))==="1");
  },[activeWorkspace?.id]);

  function hide(){
    if(!activeWorkspace?.id)return;
    window.localStorage.setItem(hiddenKey(activeWorkspace.id),"1");
    setHidden(true);onHidden?.();
  }
  function restore(){
    if(!activeWorkspace?.id)return;
    window.localStorage.removeItem(hiddenKey(activeWorkspace.id));
    setHidden(false);
  }

  if(state.loading)return variant==="full"?<div className="onboardingLoading">Checking workspace setup…</div>:null;

  if(!canBuild && variant==="compact") return null;

  if(!canBuild){
    return <section className={`workspaceGuide ${variant==="full"?"workspaceGuideFull":""}`}>
      <div className="workspaceGuideHeader"><div><p className="eyebrow">YOUR WORKSPACE</p><h2>Start from trusted content</h2><p>Your {role || "current"} role is oriented to consuming and analyzing existing workspace content. Setup actions that require Builder/Admin permissions are intentionally hidden.</p></div></div>
      <div className="consumerStartGrid">
        <Link href="/app/data-assets"><strong>Browse Catalog</strong><span>Understand available governed data.</span></Link>
        <Link href="/app/analytics"><strong>Explore analyses</strong><span>Review analytical questions and results.</span></Link>
        <Link href="/app/analytics"><strong>Open analytics</strong><span>Consume shared decision views.</span></Link>
      </div>
    </section>;
  }

  if(variant==="compact" && (hidden || done)) return null;

  return <section className={`workspaceGuide ${variant==="full"?"workspaceGuideFull":""}`}>
    <div className="workspaceGuideHeader">
      <div><p className="eyebrow">{done?"WORKSPACE READY":"GET TO YOUR FIRST DECISION VIEW"}</p><h2>{done?"Your core analytics workflow is ready":"Workspace setup guide"}</h2><p>{done?"The core path is complete. Continue with ML, optimization, governance or deeper analysis as needed.":"Follow the shortest path from connected data to a reusable dashboard. Prepare is optional when source data is already analysis-ready."}</p></div>
      <div className="workspaceGuideProgress"><strong>{progress}%</strong><span>{completed}/{required.length} required milestones</span></div>
    </div>
    {state.error?<p className="workspaceGuideWarning">{state.error}</p>:null}
    <div className="workspaceGuideBar"><span style={{width:`${progress}%`}} /></div>
    <div className="workspaceGuideSteps">{steps.map((step,index)=><article className={`workspaceGuideStep ${step.complete?"complete":""} ${!step.required?"optional":""}`} key={step.id}>
      <span className="workspaceGuideIndex">{step.complete?"✓":index+1}</span>
      <div><strong>{step.label}{!step.required?<em>Optional</em>:null}</strong><p>{step.description}</p></div>
      <Link href={step.complete&&step.completeHref?step.completeHref:step.href}>{step.complete?"Open":step.action} →</Link>
    </article>)}</div>
    <div className="workspaceGuideFooter">
      <span>Progress is inferred from real workspace objects, not manually checked tasks.</span>
      {variant==="compact"?<><Link href="/app/get-started">Open full guide</Link><button type="button" onClick={hide}>Hide guide</button></>:hidden?<button type="button" onClick={restore}>Show guide on Home again</button>:null}
    </div>
  </section>;
}
