"use client";
import {useRef} from "react";
import {updateVisualGeometry} from "@/lib/visualGeometry";

const clamp=(n,min,max)=>Math.max(min,Math.min(max,n));
export function defaultVisualSize(type){
 if(type==="KPI")return {width:260,height:160};
 if(["PIE","DONUT","TREEMAP","PACKED_BUBBLES"].includes(type))return {width:380,height:300};
 if(["TABLE","HIGHLIGHT_TABLE","HEATMAP"].includes(type))return {width:560,height:320};
 return {width:520,height:280};
}
export default function ResizableVisual({position,size,onPosition,onSize,editable=true,children,style,...props}){
 const gesture=useRef(null);
 function start(event,edge="move"){
  if(!editable||event.button!==0)return;
  if(edge==="move"&&event.target.closest("button,input,select,textarea,a"))return;
  event.preventDefault();event.stopPropagation();
  const frame=event.currentTarget.closest(".analyticsVisualBlock");
  gesture.current={edge,x:event.clientX,y:event.clientY,position:{...position},size:{...size},width:frame.parentElement.clientWidth,height:frame.parentElement.clientHeight};
  frame.setPointerCapture(event.pointerId);
 }
 function move(event){
  const g=gesture.current;if(!g)return;
  const next=updateVisualGeometry(g,event.clientX-g.x,event.clientY-g.y);
  onPosition(next.position);if(g.edge!=="move")onSize(next.size);
 }
 function finish(event){gesture.current=null;if(event.currentTarget.hasPointerCapture(event.pointerId))event.currentTarget.releasePointerCapture(event.pointerId)}
 return <div {...props} style={{...style,left:position.x,top:position.y,width:size.width,height:size.height}} onPointerDown={start} onPointerMove={move} onPointerUp={finish} onPointerCancel={finish} onLostPointerCapture={()=>{gesture.current=null}}>
  {children}
  {editable&&["n","ne","e","se","s","sw","w","nw"].map(edge=><button key={edge} type="button" className={`visualResizeGrip grip-${edge}`} aria-label={`Resize chart ${edge}`} title="Drag to resize" onPointerDown={event=>start(event,edge)} onKeyDown={event=>{if(!["ArrowLeft","ArrowRight","ArrowUp","ArrowDown"].includes(event.key))return;event.preventDefault();event.stopPropagation();const step=event.shiftKey?20:5;onSize({width:clamp(size.width+(event.key==="ArrowRight"?step:event.key==="ArrowLeft"?-step:0),180,960-position.x),height:clamp(size.height+(event.key==="ArrowDown"?step:event.key==="ArrowUp"?-step:0),120,600-position.y)})}}/>)}
 </div>
}
