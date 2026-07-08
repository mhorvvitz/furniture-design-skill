# Mechanism pieces

Furniture with a **moving mass** — a lift-lid, a flip-top, a fold-down desk, a
Murphy bed, a TV lift, a drawer under a well. These recur, and every mechanism
decision (which hinge, how strong a strut, how much clearance, how the drawer
sits under the mechanism) follows a small set of patterns. The skill's ethos holds
here: every force/torque number is **sourced or marked `assumed`** (hard rule 13) —
you size the mechanism, the supplier's calculator confirms it.

This file is read at **stage 4** when the piece has any moving part. The spec
vocabulary that expresses these — `kind="fixture"` (the TV/appliance the mechanism
serves), `joint="piano_hinge"`/`"gas_strut"` (override classification),
`motion={...}` (drive the 2D open-state + 3D toggle) — is in `carcass.py` /
`assembly.py`; this file is the *reasoning* behind choosing them.

## Draw the mechanism envelope BEFORE the structure (the clearance-stack rule)

The single most expensive mistake is placing structure first and discovering the
mechanism doesn't fit. Reverse it:

1. Draw the **moving part in every position** (closed, open, and mid-swing) and the
   **swing arc** its edges sweep.
2. Add the **served object's envelope** (the TV + its VESA bracket standoff, the
   mattress, the appliance) with real measured clearances around it.
3. **Only then** place carcass structure — sides, aprons, dividers, drawer boxes —
   in the space that's left.

On the hidden-TV coffee table this is exactly the lesson that widened the table
from 600→660 before anything was drawn: a 43″ panel plus bracket standoff would
not clear the aprons in the original width. A short center divider was stopped to
clear the TV, which then left a facade gap (caught late in 3D) — run
`carcass.check_facade_coverage()` after stopping any member short.

**Clearance stack** (sum these, don't eyeball): served-object depth + bracket
standoff + hinge/strut swing + fingers (≥ 25 mm to reach in) + a tolerance margin.
If the stack exceeds the interior, the piece grows — it does not get "made to fit."

## Pivoting-mass torque (sizing a lid stay / gas strut)

A lid or flap that pivots about a hinge needs a counter-force so it neither slams
nor flies open. The static holding torque about the hinge axis is:

```
M = m · g · d_cg
    m    = mass of the moving assembly (kg)  — lid panel + any glass/TV/hardware on it
    g    = 9.81 m/s²
    d_cg = horizontal distance from the hinge axis to the assembly's centre of
           gravity, in the position being checked (m)
```

`d_cg` is **largest near horizontal** (lid open flat) and shrinks toward closed —
so a gas strut sized for the open position is what matters, and the torque curve is
why gas struts (roughly constant force) suit lids better than a plain spring.

Worked example — a flip-top lid: panel 1260×420×20 mm white-oak veneer ply ≈ 6.4
kg, hinged along its back edge, cg ≈ 210 mm from the hinge when open flat:
`M ≈ 6.4 · 9.81 · 0.210 ≈ 13.2 N·m`. With two struts sharing it and each strut
mounted ~200 mm from the hinge, each needs ≈ `13.2 / 2 / 0.2 ≈ 33 N` of force —
**mark this `assumed`** and confirm against the strut supplier's online lid-stay
calculator (they account for mounting geometry and the force curve you can't get
from the static number). Never emit a strut force as if it were a verified spec.

If the lid carries a display (a TV on the underside), include its mass **and** its
offset in `m` and `d_cg` — a 12 kg TV at 300 mm dominates the panel's own torque.

## Hinge selection for lids and flaps

| Hinge | Use when | Notes |
|---|---|---|
| **Piano (continuous) hinge** | Long lids/flaps needing even support along the whole edge (flip-tops, chest lids) | Distributes load; screw pitch per datasheet; mount inset from the edge by the leaf width. No fixed drilling grid — mark "mount per datasheet". |
| **Euro flap / lift-up hinge** (Blum Aventos-class) | Upward-opening cabinet flaps where you want the mechanism + stay integrated | The mechanism *is* the strut — sized from a Blum-style chart by flap height × weight. Follow the chart, don't compute a strut separately. |
| **Sewing-machine / drop-lid hinge** | A lid that must fold back flush or drop below the top line | Specialised geometry; verify the swing against the clearance stack above. |

For a lid that just rests closed on an apron (no structural joint at that contact),
set `joint="none"` on the lid part so `assembly.py` doesn't invent a joint there —
the piano hinge is the only real connection and it's a mount-per-datasheet item.

## Drawer under a mechanism (the well/lift default)

When a well, TV, or lift owns the top of the interior, the drawer beneath it has a
**tall facade but a short box**: the front fills the visible facade for looks; the
box rises only to the mechanism floor so it clears. Do not let the box height
derive from the opening. Set `carcass.drawers(front_h=<facade>, box_h=<short>)` —
the helper warns if the box would rise above its own front. See the "Applied
fronts and the hidden-mechanism drawer" note in `construction-knowledge.md`.

## Racking on leg-and-apron pieces with a lifting top

A leg-and-apron table with a heavy pivoting top takes **racking loads** a static
table never sees — every lift twists the frame at the leg↔apron joints. Reinforce:

- **Corner blocks** glued/screwed into each leg↔apron corner (the standard
  anti-rack fix), or
- **Doubled dowels** / a drawbore at the apron tenons rather than a single Ø8.
- Keep the hinge and strut mounts on **solid backing** (a full-thickness apron or a
  doubler), never on a thin panel that will pull its screws under the cyclic load.

Mark the reinforcement in the assembly plan; it's structural, not decorative.
