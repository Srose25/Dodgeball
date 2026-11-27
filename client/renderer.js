/** Display-only renderer for authoritative server snapshots. */
export class CanvasRenderer {
  /** Create a renderer whose logical coordinates match the server stage. */
  constructor(canvas){this.canvas=canvas;this.context=canvas.getContext('2d');this.width=1280;this.height=720;this.resizeObserver=new ResizeObserver(()=>this.resize());this.resizeObserver.observe(canvas.parentElement);this.resize()}
  /** Resize the drawing surface without changing simulation coordinates. */
  resize(){const r=this.canvas.parentElement.getBoundingClientRect(),d=window.devicePixelRatio||1;this.canvas.width=Math.max(1,Math.round(r.width*d));this.canvas.height=Math.max(1,Math.round(r.height*d));const s=Math.min(r.width/this.width,r.height/this.height),x=(r.width-this.width*s)/2,y=(r.height-this.height*s)/2;this.context.setTransform(d*s,0,0,d*s,d*x,d*y)}
  /** Draw a snapshot; interpolation is visual only and never feeds commands. */
  draw(current,previous=null,alpha=1){const c=this.context;c.clearRect(0,0,this.width,this.height);c.fillStyle='#0b1622';c.fillRect(0,0,this.width,this.height);c.strokeStyle='#58738c';c.lineWidth=5;c.strokeRect(14,14,this.width-28,this.height-28);const op=new Map((previous?.players||[]).map(p=>[p.id,p])),ob=new Map((previous?.balls||[]).map(b=>[b.id,b]));for(const b of current.balls||[]){const f=ob.get(b.id)||b;this.circle(c,this.mix(f.x,b.x,alpha),this.mix(f.y,b.y,alpha),14,'#f3f6f8')}for(const p of current.players||[]){const f=op.get(p.id)||p;this.circle(c,this.mix(f.x,p.x,alpha),this.mix(f.y,p.y,alpha),25,p.color||'#9fb2c9');if(p.id===current.active_player_id){c.strokeStyle='#f8cd68';c.lineWidth=4;c.stroke()}}}
  circle(c,x,y,r,color){c.beginPath();c.fillStyle=color;c.arc(x,y,r,0,Math.PI*2);c.fill()}mix(a,b,t){return a+(b-a)*t}
  /** Release the resize observer. */ destroy(){this.resizeObserver.disconnect()}
}
