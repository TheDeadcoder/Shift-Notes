import json
from fractions import Fraction
from itertools import product

import pytest

from swarmgate.e1 import analysis


def test_wilson_fisher_and_kappa_match_known_values():
    lo, hi = analysis.wilson(0, 30)
    assert lo == 0 and hi == pytest.approx(0.114, abs=0.001)
    assert analysis.fisher(3, 1, 1, 3) == pytest.approx(0.486, abs=0.001)
    assert analysis.kappa([(True, True), (False, False)] * 5) == 1.0
    assert analysis.kappa([(True, False), (False, True)] * 5) < 0


def test_vignette_report_reads_responses_codes_and_the_cr1_rule(tmp_path):
    responses, codes = [], []
    for i in range(10):
        cell = f"1-interpreter-{i}"
        responses.append({"model": "m", "cell_id": cell, "good_faith": True, "resolution": "interpreter"})
        flags = {f: False for f in analysis.FLAGS} | {"recipe": i == 0, "disclosure": "D3"}
        codes.append({"cell_id": f"m|{cell}", "codes": flags})
    (tmp_path / "responses.jsonl").write_text("".join(json.dumps(r) + "\n" for r in responses))
    (tmp_path / "codes-gemini.jsonl").write_text("".join(json.dumps(r) + "\n" for r in codes))
    report = "\n".join(analysis.vignette_report(tmp_path))
    assert "p_r 1/10 = 0.10" in report and "keep the instruction" in report


def test_signflip_and_bootstrap():
    assert analysis.signflip([1.0] * 13) == 1 / 8192
    assert analysis.signflip([0.25, -0.25]) == 0.75
    lo, hi = analysis.bootstrap([[0.5] * 5], lambda a: sum(a) / len(a), reps=200)
    assert lo == hi == 0.5


def test_potency_report_runs_h1_and_h2():
    def row(kind, arm, lineage, shift, shared):
        scores = {o: 0 for o in analysis.EXACT} | {o: int(i < shared) for i, o in enumerate(analysis.SHARED)}
        return {"kind": kind, "arm": arm, "lineage": lineage, "shift": shift, **scores}

    rows = [row(k, "none", None, None, 0) for k in ("syn", "effect")] + [row(k, "positive", None, None, 4) for k in ("syn", "effect")]
    for j in range(13):
        rows += [row("syn", "A1", j, 4, 2), row("syn", "A4", j, 4, 0), row("effect", "A1", j, 4, 0), row("effect", "A4", j, 4, 0)]
    report = "\n".join(analysis.potency_report(rows))
    assert "mean A1 - A4 = 0.500 over 13 yoked pairs" in report and "p = 0.0001" in report
    assert "transfer ratio syn 0.500 vs effect 0.000" in report
    assert "exploratory (effect, g4): mean A1 - A4 = 0.000" in report
    assert "unscaled SYN minus effect difference in A1 - A4 = 0.500" in report
    assert "H2: not estimable" in "\n".join(analysis.potency_report([r for r in rows if r["arm"] != "positive"]))


def test_signflip_is_exact_and_handles_many_pairs():
    diffs = [0.25, -0.5, 1 / 3, 0.75, 0.0, -1 / 12, 0.5]
    brute = sum(sum(d if m >> i & 1 else -d for i, d in enumerate(diffs)) >= sum(diffs) - 1e-12
                for m in range(2 ** len(diffs))) / 2 ** len(diffs)
    assert analysis.signflip(diffs) == pytest.approx(brute)
    assert analysis.signflip([k / 12 for k in range(1, 33)]) == 1 / 2 ** 32


def test_signflip_counts_ties_when_scores_are_twelfths():
    assert analysis.signflip([1 / 12] * 4) == 1 / 16
    fracs = [Fraction(k, 12) for k in (1, 4, 7, 10, 1, 4, -7, 10, 5, -2)]
    brute = sum(sum(s * f for s, f in zip(signs, fracs)) >= sum(fracs)
                for signs in product((1, -1), repeat=len(fracs))) / 2 ** len(fracs)
    assert analysis.signflip([float(f) for f in fracs]) == brute


def test_holm_adjusts_in_order_and_stays_monotone():
    adjusted = analysis.holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert adjusted == pytest.approx({"a": 0.03, "c": 0.06, "b": 0.06})
    assert analysis.holm({"a": 0.6, "b": 0.9})["b"] == 1.0


def test_contrast_pairs_by_key_and_tests_one_sided():
    a = {0: 1.0, 1: 0.5, 2: 0.75, 9: 1.0}
    b = {0: 0.0, 1: 0.25, 2: 0.25, 7: 1.0}
    result = analysis.contrast(a, b)
    assert result["n"] == 3 and result["mean"] == pytest.approx(0.5833, abs=1e-4)
    assert result["p"] == pytest.approx(1 / 8) and result["low"] <= result["mean"] <= result["high"]
    assert analysis.contrast({}, b)["n"] == 0


def test_retained_share_resamples_lineages_jointly():
    before = {j: 0.5 for j in range(10)}
    after = {j: 0.25 for j in range(10)}
    result = analysis.retained_share(after, before)
    assert result["share"] == pytest.approx(0.5) and result["low"] == pytest.approx(0.5) == result["high"]
    undefined = analysis.retained_share({0: 0.5}, {0: 0.0})
    assert undefined["share"] != undefined["share"]

