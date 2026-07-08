#!/usr/bin/env python3
"""draw.py — 2D shop-drawing emitter.

Reads the positioned-part spec from carcass.py and projects elevations to a
dimensioned SVG. Auto-dimensions the overall envelope and the clear bay heights
between horizontal panels — the numbers a carpenter needs.

Three views, all from the one spec:
  draw(spec, path)   — front (XY) + side (ZY) elevations. `states=True` adds an
                       open-state side elevation for parts carrying a `motion`
                       dict (lift-lids, sliding drawers).
  plan(spec, path)   — top-down (XZ) plan with overall W/D dimension chains.

Honest limit: dimension auto-placement is the hard, unsolved part of drafting.
This produces correct, readable drawings, not draughtsman-grade layout. For dense
pieces some labels sit plainer than a hand-tuned drawing.
"""
import math

INK="#333"; MUT="#666"; DIM="#b03a2e"; PANEL="#e9e4d8"; FILL="#f6f3ec"; ROD="#1f6feb"
FIX="#c7c4cc"          # fixtures (TV, appliance): muted, clearly not a cut part
HIDDEN_KIND={"door"}

# fixed layout chrome (px) — the non-scaling margins around the drawing
_LEFT=150.0; _GAP=80; _RIGHT=230; _CHROME=_LEFT+_GAP+_RIGHT   # = 460

def _svg(w,h,title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            'font-family="Arial,Helvetica,sans-serif">'
            f'<rect width="{w}" height="{h}" fill="#fff"/>'
            '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            f'orient="auto-start-reverse"><path d="M1 1L9 5L1 9" fill="none" stroke="{DIM}" stroke-width="1.4"/></marker></defs>'
            f'<text x="22" y="30" font-size="16" font-weight="bold" fill="{INK}">{title}</text>')
def _rect(x,y,w,h,fill=PANEL):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w,0.3):.1f}" height="{max(h,0.3):.1f}" fill="{fill}" stroke="{INK}" stroke-width="1"/>'
def _rect_dashed(x,y,w,h,stroke=MUT):
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w,0.3):.1f}" height="{max(h,0.3):.1f}" '
            f'fill="none" stroke="{stroke}" stroke-width="1" stroke-dasharray="5 3"/>')
def _txt(x,y,s,size=12,fill=INK,anc="start"):
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anc}">{s}</text>'
def _vdim(x,y1,y2,lab):
    return (f'<line x1="{x:.1f}" y1="{y1:.1f}" x2="{x:.1f}" y2="{y2:.1f}" stroke="{DIM}" stroke-width="1" '
            'marker-start="url(#a)" marker-end="url(#a)"/>'+_txt(x-5,(y1+y2)/2+4,lab,11,DIM,"end"))
def _hdim(y,x1,x2,lab):
    return (f'<line x1="{x1:.1f}" y1="{y:.1f}" x2="{x2:.1f}" y2="{y:.1f}" stroke="{DIM}" stroke-width="1" '
            'marker-start="url(#a)" marker-end="url(#a)"/>'+_txt((x1+x2)/2,y-6,lab,11,DIM,"middle"))
def _ext(x1,y1,x2,y2):
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{MUT}" stroke-width="0.6"/>'

def _fill_for(p):
    if p.get("kind")=="fixture": return FIX
    if p.get("kind") in HIDDEN_KIND: return FILL
    return PANEL

def _horiz_panels(parts):
    """parts whose thinnest axis is Y (shelves/tops/bottoms), sorted by y."""
    hp=[p for p in parts if p.get("kind") not in ("rod","fixture") and min(p["sx"],p["sy"],p["sz"])==p["sy"]]
    return sorted(hp,key=lambda p:p["y"])

def _fit_scale(W, H, D, max_w, max_h):
    """P0-6: scale to fit BOTH axes, not height alone. A low, wide piece
    (coffee table, bed, sideboard) no longer blows the canvas width."""
    s_h = 700.0 / H                              # readable target height
    s_w = (max_w - _CHROME) / (W + D)            # keep front+side within max_w
    s_hc = (max_h - 150.0) / H                   # keep within max_h
    return max(0.05, min(s_h, s_w, s_hc))

def draw(spec, path, internal=False, title=None, states=False, max_w=1600, max_h=1000):
    O=spec["overall"]; W,H,D=O["W"],O["H"],O["D"]
    parts=[p for p in spec["parts"] if not (internal and p.get("kind") in HIDDEN_KIND)]
    s=_fit_scale(W,H,D,max_w,max_h)
    fx0=_LEFT; yb=60+H*s                          # front left / floor
    gap=_GAP; sx0=fx0+W*s+gap                      # side view left
    def FX(x): return fx0+x*s
    def SX(z): return sx0+z*s
    def Y(y):  return yb-y*s
    moved=[p for p in parts if p.get("motion")] if states else []
    open_h = (H*s+120) if moved else 0
    Wp,Hp = sx0+D*s+230, yb+90+open_h
    o=[_svg(Wp,Hp, title or f'{spec["name"]} — front + side elevation · mm')]
    o.append(_txt(fx0+W*s/2,52,"front",11,MUT,"middle"))
    o.append(_txt(sx0+D*s/2,52,"side",11,MUT,"middle"))
    # front: all parts as XY rects (rods as blue lines)
    for p in parts:
        if p.get("kind")=="rod":
            o.append(f'<line x1="{FX(p["x"]):.1f}" y1="{Y(p["y"]):.1f}" x2="{FX(p["x"]+p["sx"]):.1f}" y2="{Y(p["y"]):.1f}" stroke="{ROD}" stroke-width="3" stroke-linecap="round"/>')
            continue
        o.append(_rect(FX(p["x"]),Y(p["y"]+p["sy"]),p["sx"]*s,p["sy"]*s, _fill_for(p)))
    # side: ZY rects
    for p in parts:
        if p.get("kind")=="rod": continue
        o.append(_rect(SX(p["z"]),Y(p["y"]+p["sy"]),p["sz"]*s,p["sy"]*s, _fill_for(p)))
    # overall dims
    o.append(_ext(fx0,Y(0),fx0-40,Y(0))); o.append(_ext(fx0,Y(H),fx0-40,Y(H)))
    o.append(_vdim(fx0-30,Y(H),Y(0),str(round(H))))
    o.append(_ext(fx0,yb,fx0,yb+55)); o.append(_ext(FX(W),yb,FX(W),yb+55))
    o.append(_hdim(yb+45,fx0,FX(W),str(round(W))))
    o.append(_ext(sx0,yb,sx0,yb+55)); o.append(_ext(SX(D),yb,SX(D),yb+55))
    o.append(_hdim(yb+45,sx0,SX(D),str(round(D))))
    # bay-height chain (clear gaps between horizontal panels) on right of front
    hp=_horiz_panels(parts); cx=FX(W)+34
    faces=sorted(set(round(p["y"]+p["sy"]) for p in hp)|{round(p["y"]) for p in hp}|{0,round(H)})
    prev=0
    for f in faces[1:]:
        clear=f-prev
        if clear>40:  # skip the panel-thickness slivers
            o.append(_ext(FX(W),Y(prev),cx,Y(prev))); o.append(_ext(FX(W),Y(f),cx,Y(f)))
            o.append(_vdim(cx,Y(f),Y(prev),str(clear)))
        prev=f
    o.append(_txt(cx+18,Y(H/2),"clear bays",11,MUT,"start"))
    # open-state side elevation (P1-1): drawn below, parts with a motion dict moved
    if moved:
        oyb=yb+90+H*s
        def OY(y): return oyb-y*s
        o.append(_txt(sx0,oyb+80,"side — open state",11,MUT,"start"))
        for p in parts:
            if p.get("kind")=="rod": continue
            mo=p.get("motion")
            base=_rect(SX(p["z"]),OY(p["y"]+p["sy"]),p["sz"]*s,p["sy"]*s, _fill_for(p))
            if not mo:
                o.append(base); continue
            if mo.get("type")=="slide":
                v=mo.get("vector",[0,0,0])
                o.append(_rect(SX(p["z"]+v[2]),OY(p["y"]+p["sy"]+v[1]),p["sz"]*s,p["sy"]*s,_fill_for(p)))
            elif mo.get("type")=="hinge":
                piv=mo.get("pivot",[p["y"],p["z"]]); ang=mo.get("angle",90)
                cxp,cyp=SX(piv[1]),OY(piv[0])
                o.append(f'<g transform="rotate({-ang:.1f} {cxp:.1f} {cyp:.1f})">{base}</g>')
                # swing arc hint
                r=math.hypot(SX(p["z"])-cxp, OY(p["y"]+p["sy"])-cyp)
                o.append(f'<path d="M {cxp:.1f} {cyp:.1f} m {-r:.1f} 0 a {r:.1f} {r:.1f} 0 0 1 {r:.1f} {-r:.1f}" fill="none" stroke="{MUT}" stroke-width="0.6" stroke-dasharray="4 3"/>')
            else:
                o.append(base)
    o.append("</svg>")
    open(path,"w",encoding="utf-8").write("".join(o))
    return path

def plan(spec, path, title=None, max_w=1600, max_h=1000):
    """Top-down (XZ) plan view with overall W (across) and D (front-to-back)
    dimension chains. Every piece needs a plan; this is the third projection to
    match draw()'s front+side."""
    O=spec["overall"]; W,H,D=O["W"],O["H"],O["D"]
    parts=spec["parts"]
    s=_fit_scale(W,D,0,max_w,max_h)              # fit W across, D down
    px0=_LEFT; pz0=70                             # plan top-left; front at bottom
    def PX(x): return px0+x*s
    def PZ(z): return pz0+(D-z)*s                 # z=0 (back) at top, z=D (front) at bottom
    Wp,Hp = PX(W)+230, PZ(0)+90
    o=[_svg(Wp,Hp, title or f'{spec["name"]} — plan (top view) · mm')]
    o.append(_txt(PX(W/2),58,"plan — front at bottom",11,MUT,"middle"))
    # draw parts as XZ rects; skip nothing (top panels naturally cover — draw
    # thin/edge parts last so they stay visible)
    order=sorted(parts,key=lambda p:-(p["sx"]*p["sz"]))   # big footprints first
    for p in order:
        if p.get("kind")=="rod":
            o.append(f'<line x1="{PX(p["x"]):.1f}" y1="{PZ(p["z"]+p["sz"]/2):.1f}" x2="{PX(p["x"]+p["sx"]):.1f}" y2="{PZ(p["z"]+p["sz"]/2):.1f}" stroke="{ROD}" stroke-width="3" stroke-linecap="round"/>')
            continue
        o.append(_rect(PX(p["x"]),PZ(p["z"]+p["sz"]),p["sx"]*s,p["sz"]*s,_fill_for(p)))
    # overall W chain (below), D chain (left)
    yb=PZ(0)
    o.append(_ext(px0,yb,px0,yb+55)); o.append(_ext(PX(W),yb,PX(W),yb+55))
    o.append(_hdim(yb+45,px0,PX(W),str(round(W))))
    o.append(_ext(px0,PZ(D),px0-40,PZ(D))); o.append(_ext(px0,PZ(0),px0-40,PZ(0)))
    o.append(_vdim(px0-30,PZ(D),PZ(0),str(round(D))))
    o.append("</svg>")
    open(path,"w",encoding="utf-8").write("".join(o))
    return path

if __name__=="__main__":
    from carcass import Carcass
    c=Carcass(800,1800,300,t=18,name="Bookshelf")
    c.sides(); c.bottom(); c.top(); c.back(4); c.shelves(4,y0=18,y1=1782)
    draw(c.spec(),"/tmp/bookshelf_front.svg")
    plan(c.spec(),"/tmp/bookshelf_plan.svg")
    print("wrote /tmp/bookshelf_front.svg + _plan.svg")
