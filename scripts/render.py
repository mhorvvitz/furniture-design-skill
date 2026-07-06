#!/usr/bin/env python3
"""render.py — 3D render emitter.

Reads the positioned-part spec (same one draw.py and cutlist read) and emits a
self-contained three.js HTML file: one box per part at its computed position,
coloured by material, with soft shadows, studio light and manual orbit (r128 has
no OrbitControls). A sibling of the 2D drawing — both from the spec, neither from
the other.
"""
import json

COLORS={"plywood_birch":"0xdcc39a","plywood_okoume":"0xd8b48c","plywood_poplar":"0xd9c7a2",
        "melamine":"0xeeece6","mdf":"0xd9cdb8","hardboard":"0xcdb488","steel":"0xb8bcc2","default":"0xd8c69a"}

def render(spec, path, title=None):
    O=spec["overall"]; W,H,D=O["W"],O["H"],O["D"]
    parts=json.dumps(spec["parts"])
    cmap=json.dumps(COLORS)
    ttl=title or spec["name"]
    html=f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>html,body{{margin:0;height:100%;background:#f1efe9;font-family:-apple-system,Arial,sans-serif;overflow:hidden}}
#c{{display:block;width:100vw;height:100vh;cursor:grab}}#c:active{{cursor:grabbing}}
#cap{{position:fixed;left:16px;bottom:14px;color:#6b695f;font-size:12px}}#cap b{{color:#39372f}}</style></head>
<body><canvas id="c"></canvas>
<div id="cap"><b>{ttl}</b><br>{W} × {H} × {D} mm · drag to rotate · scroll to zoom</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
const PARTS={parts}, CMAP={cmap}, W={W},H={H},D={D};
const T=THREE,R=new T.WebGLRenderer({{canvas:c,antialias:true}});
R.shadowMap.enabled=true;R.shadowMap.type=T.PCFSoftShadowMap;R.outputEncoding=T.sRGBEncoding;
R.toneMapping=T.ACESFilmicToneMapping;R.toneMappingExposure=1.05;
const scene=new T.Scene();scene.background=new T.Color(0xf1efe9);const root=new T.Group();scene.add(root);
const mats={{}};function mat(k){{if(!mats[k]){{const c=parseInt(CMAP[k]||CMAP.default);
  mats[k]=(k==='steel')?new T.MeshStandardMaterial({{color:c,roughness:0.35,metalness:0.85}})
    :new T.MeshStandardMaterial({{color:c,roughness:0.75,metalness:0}});}}return mats[k];}}
const edge=new T.LineBasicMaterial({{color:0x8a7f66,transparent:true,opacity:0.32}});
PARTS.forEach(p=>{{
  if(p.kind==='rod'){{const g=new T.Mesh(new T.CylinderGeometry(p.sy/2,p.sy/2,p.sx,16),mat('steel'));
    g.rotation.z=Math.PI/2;g.position.set(p.x+p.sx/2,p.y+p.sy/2,p.z+p.sz/2);g.castShadow=true;root.add(g);return;}}
  const g=new T.Mesh(new T.BoxGeometry(p.sx,p.sy,p.sz),mat(p.material));
  g.position.set(p.x+p.sx/2,p.y+p.sy/2,p.z+p.sz/2);g.castShadow=true;g.receiveShadow=true;root.add(g);
  const e=new T.LineSegments(new T.EdgesGeometry(g.geometry),edge);e.position.copy(g.position);root.add(e);
}});
const ground=new T.Mesh(new T.PlaneGeometry(40000,40000),new T.MeshStandardMaterial({{color:0xe6e4dd,roughness:1}}));
ground.rotation.x=-Math.PI/2;ground.receiveShadow=true;scene.add(ground);
scene.add(new T.HemisphereLight(0xffffff,0xbcbab2,0.55));scene.add(new T.AmbientLight(0xffffff,0.18));
const key=new T.DirectionalLight(0xffffff,2.1);key.position.set(W*1.4,H*1.5,D*4+1500);key.castShadow=true;
key.shadow.mapSize.set(2048,2048);key.shadow.bias=-0.0004;
Object.assign(key.shadow.camera,{{near:100,far:H*5,left:-W*2,right:W*2,top:H*1.6,bottom:-H*0.4}});scene.add(key);
const fill=new T.DirectionalLight(0xffffff,0.5);fill.position.set(-W*1.6,H*0.8,D*2);scene.add(fill);
const cam=new T.PerspectiveCamera(40,1,10,60000);const tgt=new T.Vector3(W/2,H/2,D/2);
let az=-0.72,pol=1.12,rad=Math.max(W,H)*2.0;
function place(){{cam.position.set(tgt.x+rad*Math.sin(pol)*Math.sin(az),tgt.y+rad*Math.cos(pol),tgt.z+rad*Math.sin(pol)*Math.cos(az));cam.lookAt(tgt);}}
const cv=R.domElement;let drag=false,px,py,idle=true;
cv.addEventListener("pointerdown",e=>{{drag=true;idle=false;px=e.clientX;py=e.clientY;cv.setPointerCapture(e.pointerId);}});
cv.addEventListener("pointerup",()=>drag=false);
cv.addEventListener("pointermove",e=>{{if(!drag)return;az-=(e.clientX-px)*0.008;pol=Math.max(0.35,Math.min(1.45,pol-(e.clientY-py)*0.006));px=e.clientX;py=e.clientY;}});
cv.addEventListener("wheel",e=>{{rad=Math.max(W*0.8,rad+e.deltaY*1.6);e.preventDefault();}},{{passive:false}});
function rz(){{R.setSize(innerWidth,innerHeight,false);R.setPixelRatio(Math.min(devicePixelRatio,2));cam.aspect=innerWidth/innerHeight;cam.updateProjectionMatrix();}}
addEventListener("resize",rz);rz();
(function loop(){{requestAnimationFrame(loop);if(idle)az-=0.0014;place();R.render(scene,cam);}})();
</script></body></html>"""
    open(path,"w",encoding="utf-8").write(html)
    return path

if __name__=="__main__":
    from carcass import Carcass
    c=Carcass(800,1800,300,t=18,name="Bookshelf")
    c.sides(); c.bottom(); c.top(); c.back(4); c.shelves(4,y0=18,y1=1782)
    render(c.spec(),"/tmp/bookshelf_render.html")
    print("wrote /tmp/bookshelf_render.html")
