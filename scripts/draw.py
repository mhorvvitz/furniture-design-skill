#!/usr/bin/env python3
"""draw.py — 2D shop-drawing emitter.

Reads the positioned-part spec from carcass.py and projects front (XY) and side
(ZY) elevations to a dimensioned SVG. Auto-dimensions the overall envelope and the
clear bay heights between horizontal panels — the numbers a carpenter needs.

Honest limit: dimension auto-placement is the hard, unsolved part of drafting.
This produces correct, readable drawings, not draughtsman-grade layout. For dense
pieces some labels sit plainer than a hand-tuned drawing.
"""
INK="#333"; MUT="#666"; DIM="#b03a2e"; PANEL="#e9e4d8"; FILL="#f6f3ec"; ROD="#1f6feb"
HIDDEN_KIND={"door"}

def _svg(w,h,title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            'font-family="Arial,Helvetica,sans-serif">'
            f'<rect width="{w}" height="{h}" fill="#fff"/>'
            '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            f'orient="auto-start-reverse"><path d="M1 1L9 5L1 9" fill="none" stroke="{DIM}" stroke-width="1.4"/></marker></defs>'
            f'<text x="22" y="30" font-size="16" font-weight="bold" fill="{INK}">{title}</text>')
def _rect(x,y,w,h,fill=PANEL):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w,0.3):.1f}" height="{max(h,0.3):.1f}" fill="{fill}" stroke="{INK}" stroke-width="1"/>'
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

def _horiz_panels(parts):
    """parts whose thinnest axis is Y (shelves/tops/bottoms), sorted by y."""
    hp=[p for p in parts if p.get("kind")!="rod" and min(p["sx"],p["sy"],p["sz"])==p["sy"]]
    return sorted(hp,key=lambda p:p["y"])

def draw(spec, path, internal=False, title=None):
    O=spec["overall"]; W,H,D=O["W"],O["H"],O["D"]
    parts=[p for p in spec["parts"] if not (internal and p.get("kind") in HIDDEN_KIND)]
    s=700.0/H                                  # scale to ~700px tall
    fx0=150.0; yb=60+H*s                        # front left / floor
    gap=80; sx0=fx0+W*s+gap                     # side view left
    def FX(x): return fx0+x*s
    def SX(z): return sx0+z*s
    def Y(y):  return yb-y*s
    Wp,Hp = sx0+D*s+230, yb+90
    o=[_svg(Wp,Hp, title or f'{spec["name"]} — front + side elevation · mm')]
    o.append(_txt(fx0+W*s/2,52,"front",11,MUT,"middle"))
    o.append(_txt(sx0+D*s/2,52,"side",11,MUT,"middle"))
    # front: all parts as XY rects (rods as blue lines)
    for p in parts:
        if p.get("kind")=="rod":
            o.append(f'<line x1="{FX(p["x"]):.1f}" y1="{Y(p["y"]):.1f}" x2="{FX(p["x"]+p["sx"]):.1f}" y2="{Y(p["y"]):.1f}" stroke="{ROD}" stroke-width="3" stroke-linecap="round"/>')
            continue
        o.append(_rect(FX(p["x"]),Y(p["y"]+p["sy"]),p["sx"]*s,p["sy"]*s, FILL if p.get("kind") in HIDDEN_KIND else PANEL))
    # side: ZY rects
    for p in parts:
        if p.get("kind")=="rod": continue
        o.append(_rect(SX(p["z"]),Y(p["y"]+p["sy"]),p["sz"]*s,p["sy"]*s, FILL if p.get("kind") in HIDDEN_KIND else PANEL))
    # overall dims
    o.append(_ext(fx0,Y(0),fx0-40,Y(0))); o.append(_ext(fx0,Y(H),fx0-40,Y(H)))
    o.append(_vdim(fx0-30,Y(H),Y(0),str(round(H))))
    o.append(_ext(fx0,yb,fx0,yb+55)); o.append(_ext(FX(W),yb,FX(W),yb+55))
    o.append(_hdim(yb+45,fx0,FX(W),str(round(W))))
    o.append(_ext(sx0,yb,sx0,yb+55)); o.append(_ext(SX(D),yb,SX(D),yb+55))
    o.append(_hdim(yb+45,sx0,SX(D),str(round(D))))
    # bay-height chain (clear gaps between horizontal panels) on right of front
    hp=_horiz_panels(parts); cx=FX(W)+34
    levels=[(0,"floor")]+[(p["y"],"b") for p in hp]+[(p["y"]+p["sy"],"t") for p in hp]+[(H,"ceil")]
    faces=sorted(set(round(p["y"]+p["sy"]) for p in hp)|{round(p["y"]) for p in hp}|{0,round(H)})
    prev=0
    for f in faces[1:]:
        clear=f-prev
        if clear>40:  # skip the panel-thickness slivers
            o.append(_ext(FX(W),Y(prev),cx,Y(prev))); o.append(_ext(FX(W),Y(f),cx,Y(f)))
            o.append(_vdim(cx,Y(f),Y(prev),str(clear)))
        prev=f
    o.append(_txt(cx+18,Y(H/2),"clear bays",11,MUT,"start"))
    o.append("</svg>")
    open(path,"w",encoding="utf-8").write("".join(o))
    return path

if __name__=="__main__":
    import sys; from carcass import Carcass
    c=Carcass(800,1800,300,t=18,name="Bookshelf")
    c.sides(); c.bottom(); c.top(); c.back(4); c.shelves(4,y0=18,y1=1782)
    draw(c.spec(),"/tmp/bookshelf_front.svg")
    print("wrote /tmp/bookshelf_front.svg")
