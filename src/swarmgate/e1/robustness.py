from collections import defaultdict
from pathlib import Path
from statistics import mean

from . import battery, family

MEASURES = (("shared objectives", tuple(battery.SHARED), "success"), ("exact objectives", tuple(battery.EXACT), "success"),
            ("all objectives", tuple(battery.GOALS), "success"), ("shared objectives, lenient parser", tuple(battery.SHARED), "lenient"),
            ("shared objectives, attempt rate", tuple(battery.SHARED), "attempt"))


def scores(rows: list[dict], objectives: tuple[str, ...], key: str) -> dict:
    per, asked = defaultdict(lambda: defaultdict(list)), defaultdict(set)
    for r in rows:
        if r["donor"] != "anchor" and r["objective"] in objectives:
            per[battery._group(r)][r["lineage"]].append(r[key])
            asked[battery._group(r)].add(r["objective"])
    return {g: {j: mean(v) for j, v in by.items()} for g, by in per.items() if asked[g] == set(objectives)}


def _gate(rows: list[dict]) -> str:
    rate = {arm: [r["success"] for r in rows if (r["donor"], r["arm"]) == ("anchor", arm) and r["objective"] in battery.SHARED]
            for arm in ("none", "positive")}
    if not all(rate.values()):
        return "no anchors"
    none, positive = mean(rate["none"]), mean(rate["positive"])
    ok = positive - none >= battery.GATE_UPLIFT and none < battery.GATE_CEILING
    return f"anchors none {none:.2f}, positive {positive:.2f} -> {'informative' if ok else 'not informative'}"


def readers(srcs: dict, folders: list[Path], donors: list[str], shifts: tuple[int, ...]) -> list[str]:
    controls = {battery._group(s) for s in srcs.values() if s.get("control")}
    lines = ["reader tests by reader and measure: estimate, 95% CI, p; then one lineage left out"]
    for folder in folders:
        rows = battery._rows(srcs, folder / "responses.jsonl", folder / "executions.jsonl")[0]
        lines.append(f"reader {rows[0]['model'] if rows else folder.name}: {_gate(rows)}")
        for name, objectives, key in MEASURES:
            per = scores(rows, objectives, key)
            for test, (label, d) in family.reader_tests(per, controls & set(per), donors, shifts)[0].items():
                spared = d["left_out"]
                lines.append(f"  {name}: {test} {label}: {d['mean']:.3f} over {d['n']} pairs, 95% CI [{d['low']:.3f}, "
                             f"{d['high']:.3f}], p = {d['p']:.4f}"
                             + (f"; {spared['low']:.3f} to {spared['high']:.3f}, p = {spared['p']:.4f}" if spared else ""))
    return lines
