from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from ..e0.observer import load_jsonl
from .analysis import contrast, holm, retained_share, signflip
from .battery import GATE_UPLIFT

SECONDARY = ("H1-OW", "H2", "H3", "H4a", "H5", "H6")
TURNS = "turns.jsonl"
CURVE = ("outcome", "before_2", "before_4")


def _find(per: dict, donor: str, arm: str, shift: int, transform: str = "") -> tuple | None:
    found = [g for g in per if (g[1], g[2], g[4], g[5], g[6]) == (donor, "syn", arm, shift, transform)]
    return found[0] if len(found) == 1 else None


def _control(controls: set, donor: str, shift: int) -> tuple | None:
    found = [c for c in controls if (c[1], c[2], c[5]) == (donor, "syn", shift)]
    return found[0] if len(found) == 1 else None


def _gap(per: dict, a: tuple, b: tuple) -> dict:
    return {j: per[a][j] - per[b][j] for j in per[a] if j in per[b]}


def reader_tests(per: dict, controls: set, donors: list[str], shifts: tuple[int, ...]) -> tuple[dict, dict | None]:
    first, last = shifts[0], shifts[-1]
    tests, share = {}, None

    def add(name: str, label: str, a: tuple | None, b: tuple | None) -> None:
        d = contrast(per[a], per[b]) if a and b else {"n": 0}
        if d["n"]:
            tests[name] = (label, d)

    for name, donor in zip(("H1", "H1-OW"), donors):
        a1, c1 = _find(per, donor, "A1", first), _control(controls, donor, first)
        add(name, f"{donor} A1@{first} - {c1[4] if c1 else ''}@{first}", a1, c1)
        if name != "H1":
            continue
        after, c8 = _find(per, donor, "A1R", last), _control(controls, donor, last)
        if last > first:
            add("H4a", f"{donor} A1R@{last} - {c8[4] if c8 else ''}@{last}", after, c8)
        if "H4a" in tests and a1 and c1:
            share = retained_share(_gap(per, after, c8), _gap(per, a1, c1))
        copies = (_find(per, donor, "A1", first, t) for t in ("audit", "guard"))
        add("H5", f"{donor} audited - guard-scoped copy of A1@{first}", *copies)
    return tests, share


def labelled(paths: list[Path]) -> dict:
    return {(r["donor"], r["kind"], r["arm"], r["generation"], r["lineage"]): r["codes"]["recipe"] and r["codes"]["labelled"]
            for path in paths for r in load_jsonl(path) if r.get("codes") and not r.get("transform")}


def _arm(lab: dict, donor: str, kind: str, arm: str, generation: int) -> dict:
    return {j: v for (d, k, a, g, j), v in lab.items() if (d, k, a, g) == (donor, kind, arm, generation)}


def class_test(lab: dict, generation: int) -> dict:
    pairs = [(v, lab[(d, "syn", a, g, j)]) for (d, k, a, g, j), v in lab.items()
             if (k, a, g) == ("effect", "A1", generation) and (d, "syn", a, g, j) in lab]
    return {"n": len(pairs), "syn": sum(s and not e for e, s in pairs), "effect": sum(e and not s for e, s in pairs),
            "p": signflip([int(s) - int(e) for e, s in pairs])}


def persistence(lab: dict, donor: str, control_arms: set, first: int, last: int) -> list[str]:
    arms = sorted({a for (d, k, a, g, _) in lab if (d, k, g) == (donor, "syn", last)})
    held = {a: _arm(lab, donor, "syn", a, last) for a in arms}
    ctrl = [a for a in arms if a in control_arms]
    if "A1R" not in held or len(ctrl) != 1:
        return []
    pairs = [(held["A1R"][j], held[ctrl[0]][j]) for j in held["A1R"] if j in held[ctrl[0]]]
    p = signflip([int(a) - int(c) for a, c in pairs])
    line = (f"H4c labelled recipe after shift {last}: A1R {sum(a for a, _ in pairs)}/{len(pairs)}, "
            f"{ctrl[0]} {sum(c for _, c in pairs)}/{len(pairs)}, p = {p:.4f}")
    start = {j for j, v in _arm(lab, donor, "syn", "A1", first).items() if v}
    kept = ", ".join(f"{a} {sum(held[a].get(j, False) for j in start)}/{sum(j in held[a] for j in start)}"
                     for a in arms if a not in control_arms)
    return [line, f"    of the lineages with one in A1 after shift {first}, still there after shift {last}: {kept}"]


def _curve(rows: list[dict]) -> str:
    return " ".join(f"{mean(r[k] for r in rows):.2f}" for k in CURVE)


def _counts(values) -> str:
    return ", ".join(f"{k} {v}" for k, v in Counter(values).most_common()) or "none"


def attempts_detail(rows: list[dict], turns: Path) -> list[str]:
    rules = {(t["episode_id"], t["turn"]): t["rule"] for t in load_jsonl(turns) if t.get("allowed") is False}
    by_arm = {arm: [r for r in rows if r["arm"] == arm] for arm in ("none", "positive", "A1", "A4")}
    lines = ["H2 by objective: success before the 1st, 2nd and 4th denial, and the rule of the first denial"]
    for arm, rs in by_arm.items():
        for oid in sorted({r["objective"] for r in rs}):
            cell = [r for r in rs if r["objective"] == oid]
            first = _counts(rules.get((r["episode_id"], r["denial_turns"][0]), "?") for r in cell if r["denial_turns"])
            lines.append(f"    {arm:<9}{oid}  {_curve(cell)}  {first}")
    lines.append("H2 by arm: success at the first command; how episodes ended; ended after the first turn on a reply that is not a command")
    for arm, rs in by_arm.items():
        if rs:
            late = _counts(r["stop"] for r in rs if r["stop"] not in ("success", "budget") and r["turns"] > 1)
            lines.append(f"    {arm:<9}{mean(r['success_turn'] == 1 for r in rs):.2f}; {_counts(r['stop'] for r in rs)}; {late}")
    return lines


def attempts_test(path: Path) -> tuple[tuple[str, dict] | None, list[str]]:
    rows = list({r["cell_id"]: r for r in load_jsonl(path)}.values())
    lines = []
    anchors = {arm: [r["outcome"] for r in rows if r["donor"] == "anchor" and r["arm"] == arm] for arm in ("none", "positive")}
    if all(anchors.values()):
        none, positive = mean(anchors["none"]), mean(anchors["positive"])
        lines.append(f"H2 anchors: none {none:.2f} ({len(anchors['none'])} attempts), positive {positive:.2f} "
                     f"({len(anchors['positive'])}) -> {'informative' if positive - none >= GATE_UPLIFT else 'not informative'}")
    files = defaultdict(list)
    for r in rows:
        if r["donor"] != "anchor":
            files[(r["arm"], r["lineage"])].append(r)
    detail = attempts_detail(rows, path.with_name(TURNS)) if rows else []
    if not files:
        return None, lines + detail
    arms = {arm: {j: rs for (a, j), rs in files.items() if a == arm} for arm in ("A1", "A4")}
    if len({len(rs) for rs in files.values()}) != 1 or set(arms["A1"]) != set(arms["A4"]) or len(files) != 2 * len(arms["A1"]):
        return None, lines + [f"H2 table is incomplete: {sum(map(len, files.values()))} attempts on {len(files)} files"]

    def rates(arm: str) -> str:
        rs = [r for by in arms[arm].values() for r in by]
        return f"{_curve(rs)} {mean(r['success_turn'] is not None for r in rs):.2f}"

    lines.append(f"H2 success before the 1st, 2nd and 4th denial and at any point: A1 {rates('A1')}; A4 {rates('A4')}")
    traffic = Counter(u["traffic"] for r in rows for u in r.get("usage_by_turn", []) if u.get("traffic"))
    if traffic:
        lines.append(f"H2 reader calls served as {dict(sorted(traffic.items()))}")
    first = next(iter(files.values()))[0]
    score = {arm: {j: mean(r["outcome"] for r in rs) for j, rs in by.items()} for arm, by in arms.items()}
    label = f"{first['donor']} several commands, A1@{first['shift']} - A4@{first['shift']}, success before the first denial"
    return (label, contrast(score["A1"], score["A4"])), lines + detail


def report(per: dict, controls: set, donors: list[str], coder_files: list[Path], control_arms: set,
           shifts: tuple[int, ...], attempts: Path | None = None) -> list[str]:
    tests, share = reader_tests(per, controls, donors, shifts)
    h2, extra = attempts_test(attempts) if attempts else (None, [])
    if h2:
        tests["H2"] = h2
    lab = labelled(coder_files)
    h6 = class_test(lab, shifts[0])
    ps = {name: tests[name][1]["p"] for name in SECONDARY if name in tests}
    if h6["n"]:
        ps["H6"] = h6["p"]
    adjusted = holm({name: ps.get(name, 1.0) for name in SECONDARY})
    lines = [f"H1 and the secondary family (Holm over {len(SECONDARY)} tests; a test with no data counts as p = 1)"]
    for name in ("H1", *SECONDARY):
        tail = "" if name == "H1" else f", Holm p = {adjusted[name]:.4f}"
        if name in tests:
            label, d = tests[name]
            lines.append(f"  {name:6} {label}: {d['mean']:.3f} over {d['n']} pairs, 95% CI [{d['low']:.3f}, {d['high']:.3f}], "
                         f"p = {d['p']:.4f}{tail}")
        elif name == "H6" and h6["n"]:
            lines.append(f"  {name:6} labelled recipe in A1 notes after shift {shifts[0]}, SYN - effect: {h6['n']} pairs, "
                         f"{h6['syn']} SYN only, {h6['effect']} effect only, p = {h6['p']:.4f}{tail}")
        else:
            lines.append(f"  {name:6} no data")
    if share:
        lines.append(f"H4b retained share: {share['share']:.2f} [{share['low']:.2f}, {share['high']:.2f}] "
                     f"over {share['n']} pairs")
    return lines + (persistence(lab, donors[0], control_arms, shifts[0], shifts[-1]) if donors else []) + extra
