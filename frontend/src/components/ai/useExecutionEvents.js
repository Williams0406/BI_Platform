"use client";
import {useEffect,useRef,useState} from "react";
import {listExecutionEvents} from "@/lib/services/executions";
export default function useExecutionEvents(executionId,{interval=1000}={}){
  const [events,setEvents]=useState([]); const [error,setError]=useState(""); const last=useRef(0);
  useEffect(()=>{setEvents([]);last.current=0;if(!executionId)return;let alive=true;
    async function poll(){try{const next=await listExecutionEvents(executionId,last.current);if(!alive)return;if(next?.length){last.current=next[next.length-1].sequence;setEvents(prev=>[...prev,...next].slice(-5000));}setError("");}catch(e){if(alive)setError(e?.response?.data?.detail||e?.message||"Live event stream unavailable.");}}
    poll();const timer=setInterval(poll,interval);return()=>{alive=false;clearInterval(timer);};
  },[executionId,interval]);
  return {events,error};
}
