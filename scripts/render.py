#!/usr/bin/env python3
"""render.py — 3D render emitter.

Reads the positioned-part spec (same one draw.py and cutlist read) and emits a
self-contained three.js HTML file: one box per part at its computed position,
coloured by material, with soft shadows, studio light and manual orbit (r128 has
no OrbitControls). A sibling of the 2D drawing — both from the spec, neither from
the other.
"""
import json

# Legacy fallbacks; the live colours come from assets/materials.json via
# carcass.material_color so a new material propagates here without editing code.
COLORS={"plywood_birch":"0xdcc39a","plywood_okoume":"0xd8b48c","plywood_poplar":"0xd9c7a2",
        "melamine":"0xeeece6","mdf":"0xd9cdb8","hardboard":"0xcdb488","steel":"0xb8bcc2",
        "fixture":"0x3a3a3e","default":"0xd8c69a"}

def _hex(rgb):
    return "0x%02x%02x%02x" % tuple(int(c) for c in rgb)

def _build_cmap(spec):
    """Per-spec material→hex map: data-file colours override the legacy defaults;
    fixtures get their muted tone."""
    cmap = dict(COLORS)
    try:
        from carcass import material_color, fixture_default_color
    except Exception:
        try:
            from .carcass import material_color, fixture_default_color
        except Exception:
            material_color = lambda *a, **k: None
            fixture_default_color = lambda: (58, 58, 62)
    for p in spec["parts"]:
        c = material_color(p["material"])
        if c:
            cmap[p["material"]] = _hex(c)
    cmap["fixture"] = _hex(fixture_default_color())
    return cmap

# --- visibility groups -------------------------------------------------------
# On an L- or U-shaped built-in you cannot see past the near run, so every part
# is tagged with a group the viewer can switch off. The default grouping is
# derived from `kind` and the `defn` prefix; a caller may pass its own
# {label: predicate} mapping instead. Order here is the order of the checkboxes.
_RENDER_GROUP_RULES = (
    (lambda p: p.get("kind") == "fixture", "Fixtures"),
    (lambda p: p.get("kind") == "rod", "Rods"),
    (lambda p: p.get("kind") == "door", "Fronts"),
    (lambda p: p.get("defn", "").startswith("Drawer"), "Drawers"),
    (lambda p: p.get("defn", "") == "Shelf", "Shelves"),
    (lambda p: p.get("defn", "") == "Back", "Back"),
)
_GROUP_ORDER = ("Carcass", "Back", "Shelves", "Drawers", "Fronts", "Rods", "Fixtures")


def group_of(part, rules=None):
    """Visibility-group label for a part. First matching rule wins; the fallback
    is 'Carcass' (sides, top, bottom, fixed panels, dividers)."""
    for pred, label in (rules or _RENDER_GROUP_RULES):
        if pred(part):
            return label
    return "Carcass"


def _tag_groups(spec, groups=None):
    """Return (parts_with_g, ordered_group_labels). `groups` is an optional
    {label: predicate} dict overriding the default rules."""
    rules = tuple((v, k) for k, v in groups.items()) if groups else None
    out = [dict(p, g=group_of(p, rules)) for p in spec["parts"]]
    present = {p["g"] for p in out}
    known = [g for g in _GROUP_ORDER if g in present]
    extra = sorted(present - set(_GROUP_ORDER))
    return out, known + extra


def render(spec, path, title=None, groups=None):
    O=spec["overall"]; W,H,D=O["W"],O["H"],O["D"]
    tagged_parts, group_labels = _tag_groups(spec, groups)
    parts=json.dumps(tagged_parts)
    grp_json=json.dumps([[f"g{i}", g] for i, g in enumerate(group_labels)])
    grp_html="".join(
        f'<label><input type="checkbox" id="g{i}" checked>{g}</label>'
        for i, g in enumerate(group_labels))
    cmap=json.dumps(_build_cmap(spec))
    ttl=title or spec["name"]
    html=f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>html,body{{margin:0;height:100%;background:#f1efe9;font-family:-apple-system,Arial,sans-serif;overflow:hidden}}
#c{{display:block;width:100vw;height:100vh;cursor:grab}}#c:active{{cursor:grabbing}}
#cap{{position:fixed;left:16px;bottom:14px;color:#6b695f;font-size:12px}}#cap b{{color:#39372f}}
#ui{{position:fixed;right:14px;top:14px;display:flex;flex-direction:column;gap:6px}}
#ui button{{font:12px/1.4 -apple-system,Arial;padding:6px 12px;border:1px solid #cbc7bd;border-radius:7px;background:#fbfaf6;color:#39372f;cursor:pointer}}
#ui button:hover{{background:#efece3}}
#vw{{display:flex;flex-wrap:wrap;gap:4px;justify-content:flex-end;max-width:200px}}
#vw button{{font:11px inherit;padding:4px 8px;border-radius:5px;border:1px solid #d8d2c6;background:#fbfaf7;cursor:pointer}}
#vw button:hover{{background:#f0ece3}}
#gr{{display:flex;flex-direction:column;gap:3px;font:11px/1.4 -apple-system,Arial;color:#39372f;
  background:#fbfaf6;border:1px solid #cbc7bd;border-radius:7px;padding:7px 10px}}
#gr .lbl{{color:#8a8175;margin-bottom:2px}}
#gr label{{display:flex;gap:6px;align-items:center;cursor:pointer}}</style></head>
<body><canvas id="c"></canvas>
<div id="ui">
<div id="vw"><button data-v="iso">Iso</button><button data-v="front">Front</button
><button data-v="left">Left</button><button data-v="right">Right</button
><button data-v="top">Top</button></div>
<div id="gr"><div class="lbl">Show</div>{grp_html}</div>
</div>
<div id="cap"><b>{ttl}</b><br>{W} × {H} × {D} mm · drag to rotate · scroll to zoom</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
const PARTS={parts}, CMAP={cmap}, W={W},H={H},D={D};
/* visibility groups: [checkboxId, label]. Every mesh AND its edge LineSegments
   register under the part's `g` label so hiding a run hides its outlines too. */
const GROUPS={grp_json};
const tagged={{}};GROUPS.forEach(gl=>tagged[gl[1]]=[]);
function reg(o,tag){{if(tag&&tagged[tag])tagged[tag].push(o);}}
const T=THREE,R=new T.WebGLRenderer({{canvas:c,antialias:true}});
R.shadowMap.enabled=true;R.shadowMap.type=T.PCFSoftShadowMap;R.outputEncoding=T.sRGBEncoding;
R.toneMapping=T.ACESFilmicToneMapping;R.toneMappingExposure=1.05;
const scene=new T.Scene();scene.background=new T.Color(0xf1efe9);const root=new T.Group();scene.add(root);
const mats={{}};function mat(k){{if(!mats[k]){{const c=parseInt(CMAP[k]||CMAP.default);
  mats[k]=(k==='steel')?new T.MeshStandardMaterial({{color:c,roughness:0.35,metalness:0.85}})
    :new T.MeshStandardMaterial({{color:c,roughness:0.75,metalness:0}});}}return mats[k];}}
const edge=new T.LineBasicMaterial({{color:0x8a7f66,transparent:true,opacity:0.32}});
// --- motion groups (P1-2): parts carrying a `motion` dict share a THREE.Group
// keyed by motion.group; hinge groups pivot, slide groups translate. No motion
// on any part => behaves exactly like the static render. ---
const mgroups={{}};
function motionGroup(p){{
  const m=p.motion; if(!m) return {{parent:root,origin:new T.Vector3(0,0,0)}};
  const name=m.group||('g_'+p.x+'_'+p.y+'_'+p.z);
  if(!mgroups[name]){{
    const g=new T.Group(); const o=new T.Vector3(0,0,0);
    if(m.type==='hinge'&&m.pivot){{o.set(0,m.pivot[0],m.pivot[1]);}}
    g.position.copy(o); g.userData={{m:m,cur:0,tgt:0,base:o.clone()}};
    mgroups[name]=g; root.add(g);
  }}
  return {{parent:mgroups[name],origin:mgroups[name].userData.base}};
}}
const EXP=[];  // meshes eligible for exploded view
PARTS.forEach(p=>{{
  const gp=motionGroup(p), par=gp.parent, o=gp.origin;
  if(p.kind==='rod'){{const g=new T.Mesh(new T.CylinderGeometry(p.sy/2,p.sy/2,p.sx,16),mat('steel'));
    g.rotation.z=Math.PI/2;g.position.set(p.x+p.sx/2-o.x,p.y+p.sy/2-o.y,p.z+p.sz/2-o.z);g.castShadow=true;par.add(g);
    reg(g,p.g);g.userData.home=g.position.clone();EXP.push(g);return;}}
  const g=new T.Mesh(new T.BoxGeometry(p.sx,p.sy,p.sz),mat(p.kind==='fixture'?'fixture':p.material));
  g.position.set(p.x+p.sx/2-o.x,p.y+p.sy/2-o.y,p.z+p.sz/2-o.z);g.castShadow=true;g.receiveShadow=true;par.add(g);
  const e=new T.LineSegments(new T.EdgesGeometry(g.geometry),edge);e.position.copy(g.position);par.add(e);
  reg(g,p.g);reg(e,p.g);
  g.userData.home=g.position.clone();g.userData.edge=e;EXP.push(g);
}});
// precompute exploded offsets: radial from model centre, scaled
const CEN=new T.Vector3(W/2,H/2,D/2);let expfac=0,exptgt=0;
EXP.forEach(g=>{{const base=(g.parent.userData&&g.parent.userData.base)||new T.Vector3();
  const wp=g.userData.home.clone().add(base);
  let dir=wp.clone().sub(CEN);if(dir.length()<1)dir.set(0,1,0);
  g.userData.expl=dir.normalize().multiplyScalar(0.35*Math.max(W,H,D));}});
const ground=new T.Mesh(new T.PlaneGeometry(40000,40000),new T.MeshStandardMaterial({{color:0xe6e4dd,roughness:1}}));
ground.rotation.x=-Math.PI/2;ground.receiveShadow=true;scene.add(ground);
scene.add(new T.HemisphereLight(0xffffff,0xbcbab2,0.55));scene.add(new T.AmbientLight(0xffffff,0.18));
const key=new T.DirectionalLight(0xffffff,2.1);key.position.set(W*1.4,H*1.5,D*4+1500);key.castShadow=true;
key.shadow.mapSize.set(2048,2048);key.shadow.bias=-0.0004;
Object.assign(key.shadow.camera,{{near:100,far:H*5,left:-W*2,right:W*2,top:H*1.6,bottom:-H*0.4}});scene.add(key);
const fill=new T.DirectionalLight(0xffffff,0.5);fill.position.set(-W*1.6,H*0.8,D*2);scene.add(fill);
const cam=new T.PerspectiveCamera(40,1,10,60000);const tgt=new T.Vector3(W/2,H/2,D/2);
const AZ0=-0.72, rad0=Math.max(W,H)*2.0;
let az=AZ0,pol=1.12,rad=rad0;
function place(){{cam.position.set(tgt.x+rad*Math.sin(pol)*Math.sin(az),tgt.y+rad*Math.cos(pol),tgt.z+rad*Math.sin(pol)*Math.cos(az));cam.lookAt(tgt);}}
const cv=R.domElement;let drag=false,px,py,idle=true;
cv.addEventListener("pointerdown",e=>{{drag=true;idle=false;px=e.clientX;py=e.clientY;cv.setPointerCapture(e.pointerId);}});
cv.addEventListener("pointerup",()=>drag=false);
cv.addEventListener("pointermove",e=>{{if(!drag)return;az-=(e.clientX-px)*0.008;pol=Math.max(0.35,Math.min(1.45,pol-(e.clientY-py)*0.006));px=e.clientX;py=e.clientY;}});
cv.addEventListener("wheel",e=>{{rad=Math.max(W*0.8,rad+e.deltaY*1.6);e.preventDefault();}},{{passive:false}});
function rz(){{R.setSize(innerWidth,innerHeight,false);R.setPixelRatio(Math.min(devicePixelRatio,2));cam.aspect=innerWidth/innerHeight;cam.updateProjectionMatrix();}}
addEventListener("resize",rz);rz();
/* Fixed view presets — declared AFTER az/pol/rad exist, because the table reads
   AZ0 and rad0. Referencing them above their `const` throws a temporal-dead-zone
   error that kills lighting, orbit and the render loop, leaving a blank canvas
   indistinguishable from slow WebGL. Locked by a test.
   Azimuths follow THIS file's place(): cam.x=tgt.x+rad*sin(pol)*sin(az),
   cam.z=tgt.z+rad*sin(pol)*cos(az). Front is at max Z, so az=0 looks straight at
   the front, az=+PI/2 is the right side, az=-PI/2 the left, and pol->0 is plan. */
const VIEWS={{iso:[AZ0,1.12,rad0], front:[0,1.45,rad0*0.92],
             left:[-Math.PI/2,1.45,rad0*0.92], right:[Math.PI/2,1.45,rad0*0.92],
             top:[0,0.12,rad0*0.98]}};
document.querySelectorAll('#vw button').forEach(b=>{{
  b.onclick=()=>{{const v=VIEWS[b.dataset.v];az=v[0];pol=v[1];rad=v[2];idle=false;}};
}});
/* Group visibility. The motion/explode code never touches .visible, so a hidden
   run stays hidden through an explode or a door swing. */
function applyVis(){{GROUPS.forEach(gl=>{{const el=document.getElementById(gl[0]);
  const on=!el||el.checked;tagged[gl[1]].forEach(o=>o.visible=on);}});}}
GROUPS.forEach(gl=>{{const el=document.getElementById(gl[0]);
  if(el)el.addEventListener('change',applyVis);}});
applyVis();
// --- UI: one toggle per motion group + Reset + Explode ---
const ui=document.getElementById('ui');
function btn(label,fn){{const b=document.createElement('button');b.textContent=label;b.onclick=fn;ui.appendChild(b);return b;}}
Object.keys(mgroups).forEach(k=>{{const u=mgroups[k].userData;btn(u.m.label||k,()=>{{u.tgt=u.tgt>0.5?0:1;}});}});
if(Object.keys(mgroups).length)btn('Reset',()=>{{for(const k in mgroups)mgroups[k].userData.tgt=0;exptgt=0;}});
btn('Explode',()=>{{exptgt=exptgt>0.5?0:1;}});
function animateMotion(){{
  for(const k in mgroups){{const G=mgroups[k],u=G.userData;u.cur+=(u.tgt-u.cur)*0.12;
    if(u.m.type==='hinge'){{G.rotation.x=-((u.m.angle||90)*Math.PI/180)*u.cur;}}
    else if(u.m.type==='slide'){{const v=u.m.vector||[0,0,0];G.position.set(u.base.x+v[0]*u.cur,u.base.y+v[1]*u.cur,u.base.z+v[2]*u.cur);}}
  }}
  expfac+=(exptgt-expfac)*0.12;
  EXP.forEach(g=>{{const h=g.userData.home,e=g.userData.expl;g.position.set(h.x+e.x*expfac,h.y+e.y*expfac,h.z+e.z*expfac);
    if(g.userData.edge)g.userData.edge.position.copy(g.position);}});
}}
(function loop(){{requestAnimationFrame(loop);if(idle)az-=0.0014;animateMotion();place();R.render(scene,cam);}})();
</script></body></html>"""
    open(path,"w",encoding="utf-8").write(html)
    return path

if __name__=="__main__":
    from carcass import Carcass
    c=Carcass(800,1800,300,t=18,name="Bookshelf")
    c.sides(); c.bottom(); c.top(); c.back(4); c.shelves(4,y0=18,y1=1782)
    render(c.spec(),"/tmp/bookshelf_render.html")
    print("wrote /tmp/bookshelf_render.html")
