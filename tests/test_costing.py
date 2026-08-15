import costing

RATES = {
    "currency": "ILS", "vat_pct": 18,
    "sheets": {"melamine_18": {"desc": "18mm melamine", "low": 200, "high": 300}},
    "banding_per_m": {"desc": "banding", "low": 4.0, "high": 8.0},
    "hardware": [{"item": "cam", "qty": 10, "low": 2.0, "high": 4.0}],
    "waste_pct": {"value": 10},
}
CUT = {"material_summary": {"melamine_18": {"parts": 5, "area": 4.0,
                                            "band_m": 10.0, "sheets_est": 2}}}


def test_boards_multiply_sheets_by_rate():
    e = costing.estimate(CUT, RATES)
    assert e["boards"] == (400.0, 600.0)


def test_banding_multiplies_metres_by_rate():
    e = costing.estimate(CUT, RATES)
    assert e["banding"] == (40.0, 80.0)


def test_hardware_multiplies_qty_by_rate():
    e = costing.estimate(CUT, RATES)
    assert e["hardware"] == (20.0, 40.0)


def test_waste_and_vat_compound_in_order():
    e = costing.estimate(CUT, RATES)
    assert e["subtotal"] == (460.0, 720.0)
    assert e["net"] == (506.0, 792.0)          # +10% waste
    assert round(e["total"][0], 2) == 597.08   # +18% VAT
    assert round(e["total"][1], 2) == 934.56


def test_unknown_material_is_reported_not_silently_zero():
    cut = {"material_summary": {"unobtainium_9": {"parts": 1, "area": 1.0,
                                                  "band_m": 0.0, "sheets_est": 1}}}
    e = costing.estimate(cut, RATES)
    assert e["missing_rates"] == ["unobtainium_9"]


def test_render_md_flags_the_estimate_as_unverified():
    md = costing.render_md(costing.estimate(CUT, RATES), RATES)
    assert "ASSUMED" in md
    assert "labour" in md.lower()
