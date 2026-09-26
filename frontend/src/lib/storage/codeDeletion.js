import {readCodeDrafts,writeCodeDraft} from "@/lib/storage/codeDrafts";
const deletedByWorkspace=new Map();
export function deletedMeasureIds(workspace){return deletedByWorkspace.get(String(workspace))||[]}

export function matchesDeletedCode(code,language,result){
 return Boolean(code?.trim())&&(result.deleted_code||[]).some(item=>item.language===language&&item.code?.trim()===code.trim());
}
export function notifyCodeDeletion(result){
 if(typeof window==="undefined"||!result?.workspace)return result;
 deletedByWorkspace.set(String(result.workspace),[...new Set([...deletedMeasureIds(result.workspace),...(result.deleted_metric_ids||[])])]);
 for(const draft of readCodeDrafts(result.workspace)){
  if((result.deleted_metric_ids||[]).includes(String(draft.metricId))||matchesDeletedCode(draft.code,draft.language,result))writeCodeDraft(result.workspace,draft.id,null);
 }
 window.dispatchEvent(new CustomEvent("bi-code-deleted",{detail:result}));
 return result;
}
