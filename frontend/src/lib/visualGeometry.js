const clamp=(n,min,max)=>Math.max(min,Math.min(max,n));
export function updateVisualGeometry(gesture,dx,dy){
 const g=gesture;
 let {x,y}=g.position;let {width,height}=g.size;
 if(g.edge==="move")return {position:{x:clamp(x+dx,0,g.width-width),y:clamp(y+dy,0,g.height-height)},size:{width,height}};
 if(g.edge.includes("e"))width=clamp(width+dx,180,g.width-x);
 if(g.edge.includes("s"))height=clamp(height+dy,120,g.height-y);
 if(g.edge.includes("w")){x=clamp(x+dx,0,x+width-180);width=g.position.x+g.size.width-x}
 if(g.edge.includes("n")){y=clamp(y+dy,0,y+height-120);height=g.position.y+g.size.height-y}
 return {position:{x,y},size:{width,height}};
}
