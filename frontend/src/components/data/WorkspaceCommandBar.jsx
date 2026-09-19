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
  actions.push({key:"save",icon:"save",label:"Save",fn:onSave});
  actions.push({key:"reading",icon:"explore",label:"Reading view",fn:onReading});
  actions.push({key:"refresh",icon:"activity",label:"Refresh",fn:onRefresh});
 }
 return <div className="workspaceCommandBar"><div className="workspaceCommandIdentity"><Icon name={view==="analytics"?"chart":view==="table"?"records":"model"} size={17}/><strong>{view==="analytics"?"Analytics":view==="table"?"Table":"Data"}</strong></div><div className="workspaceCommandActions">{children}{actions.map(a=><button key={a.key} type="button" className={`modelIconAction ${a.active?"active":""}`} title={a.label} aria-label={a.label} onClick={a.fn}><Icon name={a.icon} size={18}/></button>)}</div></div>;
}
