#!/usr/bin/env python3
"""costing.py — materials + hardware estimate, derived from the cut list.

DERIVED, not authored: reads cutlist.py's JSON output and assets/rates.json, so
the estimate cannot drift from the parts. Every rate is an ASSUMED market price;
carpenter labour, delivery and installation are excluded.
"""
import json
import os


def estimate(cutlist_json, rates):
    """(low, high) money tuples for each cost line."""
    summary = cutlist_json["material_summary"]
    missing = []
    b_lo = b_hi = 0.0
    for mid, s in summary.items():
        r = rates["sheets"].get(mid)
        if r is None:
            missing.append(mid)
            continue
        b_lo += s["sheets_est"] * r["low"]
        b_hi += s["sheets_est"] * r["high"]

    band_m = sum(s.get("band_m", 0.0) for s in summary.values())
    bp = rates["banding_per_m"]
    band = (band_m * bp["low"], band_m * bp["high"])

    h_lo = sum(h["qty"] * h["low"] for h in rates["hardware"])
    h_hi = sum(h["qty"] * h["high"] for h in rates["hardware"])

    sub = (b_lo + band[0] + h_lo, b_hi + band[1] + h_hi)
    w = rates["waste_pct"]["value"] / 100.0
    waste = (sub[0] * w, sub[1] * w)
    net = (sub[0] + waste[0], sub[1] + waste[1])
    v = rates["vat_pct"] / 100.0
    vat = (net[0] * v, net[1] * v)
    total = (net[0] + vat[0], net[1] + vat[1])

    return {"boards": (b_lo, b_hi), "banding": band, "hardware": (h_lo, h_hi),
            "subtotal": sub, "waste": waste, "net": net, "vat": vat,
            "total": total, "band_m": band_m, "missing_rates": missing}


def render_md(est, rates):
    cur = rates.get("currency", "?")
    L = ["# Materials cost estimate\n",
         f"Currency: **{cur}**. Derived from the cut list + `assets/rates.json`.\n",
         "> **Every rate below is an ASSUMED market price, not a quote.** Replace",
         "> them with real supplier prices before committing money. Carpenter",
         "> labour, delivery and installation are NOT included — on fitted work",
         "> they are usually the larger half of the bill.\n"]
    if est["missing_rates"]:
        L.append(f"\n> **NO RATE for: {', '.join(est['missing_rates'])}** — "
                 f"add them to `assets/rates.json`; they are excluded below.\n")
    L.append(f"\n| Line | {cur} low | {cur} high |")
    L.append("|---|---:|---:|")
    for k in ("boards", "banding", "hardware", "subtotal", "waste", "net", "vat", "total"):
        L.append(f"| {k.title()} | {est[k][0]:,.0f} | {est[k][1]:,.0f} |")
    return "\n".join(L)


def main(cutlist_path, rates_path, out_path):
    cut = json.load(open(cutlist_path, encoding="utf-8"))
    rates = json.load(open(rates_path, encoding="utf-8"))
    est = estimate(cut, rates)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(render_md(est, rates))
    return est


if __name__ == "__main__":
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    default_rates = os.path.join(here, "..", "assets", "rates.json")
    a = sys.argv[1:]
    if not a:
        raise SystemExit("usage: costing.py <cutlist.json> [rates.json] [out.md]\n"
                         f"       rates default: {os.path.normpath(default_rates)}")
    est = main(a[0], a[1] if len(a) > 1 else default_rates,
               a[2] if len(a) > 2 else "cost.md")
    if est["missing_rates"]:
        print(f"NO RATE for: {', '.join(est['missing_rates'])} — excluded from the "
              f"totals; add them to assets/rates.json", file=sys.stderr)
