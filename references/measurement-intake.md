# Measurement Intake

The point of this stage is to get **trustworthy numbers** into the spec. Design
intent can come from talk and pictures; cut dimensions cannot. This file is the
checklist for extracting real numbers from the user without guessing.

## Why images are useless for dimensions (say this when needed)

A photo has no scale reference, lens distortion bends straight lines, and the
camera angle hides depth. A hand sketch is proportional at best. Neither can be
trusted to a millimetre, and furniture that is wrong by a few millimetres either
does not fit the niche or has doors that bind. So: pictures set the *look*, the
user's tape measure sets the *size*. Offer to tell them exactly what to measure.

## Built-ins (closets, wall units, kitchens, ארונות קיר)

Built-ins live inside an opening that is never a perfect rectangle. Capture the
opening, not "the size".

Width — measure at **three heights** (floor, mid, ceiling). Walls bow and lean.
- Use the **smallest** width as the controlling dimension; the gap is taken up by
  scribe/filler (see construction reference).

Height — measure at **three positions** (left, centre, right). Floors slope and
ceilings drop.
- Use the **smallest** height as controlling.

Depth — measure the usable depth, and note anything that eats into it
(skirting/פנל, pipes, a windowsill, an electrical conduit).

Square check — measure both **diagonals** of the opening. Equal diagonals = a
square opening; unequal = out of square, and the scribe allowance must grow.

Out-of-level / out-of-plumb — note which way the floor slopes and whether walls
lean in or out. This decides which end gets scribed and whether the toe-kick is
tapered.

Obstructions and services — mark and dimension: שקעים/מתגים (sockets/switches),
מזגן and its piping, water/drain stubs, radiators, window/door trim, beams,
intercom, ceiling step. A built-in that covers a socket the user still needs is a
redesign.

Fixing context — what are the walls made of (block/בלוק, drywall/גבס, concrete)?
It changes the fixings and whether a French cleat or direct screw is viable.

Access — for delivery/installation: door widths, corridor turns, stairs, lift.
A 2.4 m one-piece carcass that cannot enter the room must be split into modules.

## Freestanding (tables, desks, shelving, beds, sideboards)

No opening to fit, so the controlling numbers are **ergonomics + envelope**.
Confirm these with the user rather than assuming; the figures below are common
defaults, not law.

Common ergonomic defaults (mm) — confirm per project:
- Dining table top height: ~750. Seat height: ~450–470. Knee clearance under
  apron: ≥620 clear. Per-diner width: ~600.
- Desk/work surface height: ~730–750 (sitting). Standing desk: ~1050–1100.
- Kitchen counter height: ~900 (Israel commonly 900; verify the client's
  appliances and sink). Bar/island overhang for stools: ~1050–1100 top.
- Shelf clear spacing: books ~250–320, paperbacks ~200, display varies.
- Bookshelf span before sag: keep ≤800 between supports for 18 mm shelves under
  load; less for heavier loads or thinner stock.
- Bed: mattress sizes are the hard constraint — get the actual mattress L×W×H
  (Israeli sizes differ from US/EU; ask, do not assume).
- Seat depth: ~450. Backrest start: ~ above seat. (Chairs are their own
  discipline; flag if the user wants real chair joinery.)

Envelope — overall L×W×H the user wants, plus any room constraints (must clear a
doorway, fit under a window, leave a walkway ≥700–900).

Load and use — what goes on/in it, and how rough the use is. Drives material,
thickness, shelf spans, and joinery strength.

## Recording into the spec

For every number, store its **source**:
- `measured` — the user measured it.
- `standard` — an agreed ergonomic/standard value.
- `assumed` — you filled it provisionally. These must be surfaced and confirmed
  before stage 5. Never let an `assumed` number silently become a cut size.

Keep the controlling built-in dimensions (smallest width/height, diagonals) in
the spec explicitly, because the construction stage subtracts scribe and
thickness from *those*, not from a friendly round number.

## When the user resists measuring

They will. "Just estimate from the photo." Hold the line: explain that an estimate
becomes a cut, a cut becomes scrap, and a 30-second measurement is cheaper than a
ruined 2800×2070 sheet. Offer the exact tape-measure steps. If they genuinely
cannot measure yet, proceed to design *proportionally* and mark the entire spec
provisional, with a loud note that no cut list is valid until real numbers land.
