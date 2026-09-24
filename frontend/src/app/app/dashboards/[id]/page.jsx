"use client";
import {useEffect,useState} from "react";
import ExploreStudio from "@/components/explore/ExploreStudio";
export default function DashboardDetailPage({params}){const [id,setId]=useState(null);useEffect(()=>{Promise.resolve(params).then(p=>setId(p.id))},[params]);if(!id)return null;return <ExploreStudio dashboardId={id}/>;}
