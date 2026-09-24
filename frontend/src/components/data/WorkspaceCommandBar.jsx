"use client";
import Icon from "@/components/ui/Icon";

export default function WorkspaceCommandBar({view="data",codeOpen=false,onToggleCode,onLineage,onActivity,onSave,onReading,onRefresh,children}){
 const actions=[];
 if(onToggleCode)actions.push({key:"code",icon:"formula",label:codeOpen?"Hide code":"Show code",fn:onToggleCode,active:codeOpen});
 if(view==="table"){
  actions.push({key:"lineage",icon:"relationship",label:"Lineage",fn:onLineage});
  actions.push({key:"activity",icon:"activity",label:"Activity",fn:onActivity});
 }
 if(view==="analytics"){
  if(onSave)actions.push({key:"save",icon:"save",label:"Save",fn:onSave});
  if(onReading)actions.push({key:"reading",icon:"explore",label:"Reading view",fn:onReading});
  if(onRefresh)actions.push({key:"refresh",icon:"activity",label:"Refresh",fn:onRefresh});
 }
 const meta=view==="analytics"?{icon:"chart",label:"Analytics"}:view==="table"?{icon:"table",label:"Table"}:view==="code"?{icon:"code",label:"Code"}:view==="operations"?{icon:"view",label:"Operations"}:{icon:"model",label:"Data"};
 return <div className="workspaceCommandBar"><div className="workspaceCommandIdentity"><Icon name={meta.icon} size={17}/><strong>{meta.label}</strong></div><div className="workspaceCommandActions">{children}{actions.map(a=><button key={a.key} type="button" className={`modelIconAction ${a.active?"active":""}`} title={a.label} aria-label={a.label} onClick={a.fn}><Icon name={a.icon} size={18}/></button>)}</div></div>;
}
