import csv
import json
from collections import defaultdict
from pathlib import Path

from ..e0.observer import load_jsonl
from . import battery, family, knowledge
from .behavior import DENIAL, ROUTE, route
from .chains import records, refused
from .notes_coding import FLAGS
from .potency import OBJECTIVES

SESSIONS, POTENCY, EDITS = "sessions.jsonl", "potency.jsonl", "edits.jsonl"
CELL = ("model", "cell_id", "donor", "kind", "arm", "lineage", "run", "shift", "generation", "transform", "objective", "sample")
RUN = ("cell_id", "allowed", "success")
KEPT = {
    "battery": {"responses.jsonl": (*CELL, "action", "refused"), "executions.jsonl": RUN, battery.LENIENT: RUN},
    "coding": {"*.jsonl": (*CELL, "codes", "refused")},
    "attempts": {"responses.jsonl": (*CELL, "reader", "phase", "episode_id", "protocol_sha256", "outcome", "before_2", "before_4",
                                     "success_turn", "denial_turns", "stop", "turns", "commands", "actions"),
                 family.TURNS: ("cell_id", "episode_id", "turn", "action", "allowed", "rule")},
    "probe": {knowledge.TABLE_FILE: (*CELL, "reader", "phase", "probe_id", "protocol_sha256", "score", "score_num", "score_den",
                                     "repaired_mean", "category_means", "status", "parsed_count", "refused"),
              knowledge.REPLY_LOG: ("cell_id", "probe_id", "reader", "donor", "arm", "lineage", "shift", "transform", "item_probs")},
}
LOGS = {family.TURNS: "episode_id", knowledge.REPLY_LOG: "probe_id"}


def _write(path: Path, rows: list[dict]) -> int:
    if rows:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    return len(rows)


def _latest(path: Path) -> list[dict]:
    return list({r["cell_id"]: r for r in load_jsonl(path)}.values())


def _session(cfg: dict, r: dict) -> dict:
    return {"donor": cfg["donor"], "kind": r["kind"], "arm": r["arm"], "lineage": r["lineage"], "shift": r["generation"] + 1,
            "b_task": r["tasks"][0], "chore": r["tasks"][1], "tickets_done": sum(r["checks"].values()),
            "calls": r["calls"], "denials": r["denials"], "workarounds": " ".join(r["workarounds"]),
            "refused": int(refused(r)), "merge_refused": int(bool(r.get("consolidation_refused"))),
            "malformed": r.get("malformed", 0)}


def _potency(cfg: dict, p: dict) -> dict:
    n = p["candidates"] if isinstance(p["candidates"], int) else len(p["candidates"])
    return {"donor": cfg["donor"], "kind": p["kind"], "arm": p["arm"], "lineage": p["lineage"],
            "shift": p["generation"], "candidates": n, **{o.id: int(p["scores"][o.id]) for o in OBJECTIVES}}


def tables(cfgs: list[dict], out: Path, battery_dirs: list[Path], coding_dir: Path) -> dict:
    sessions, potency, codes, trials = [], [], [], []
    for cfg in cfgs:
        run = Path(cfg["out"])
        sessions += [_session(cfg, r) for r in records(run)]
        potency += [_potency(cfg, p) for p in load_jsonl(run / "potency.jsonl")]
    for path in sorted(coding_dir.glob("codes-*.jsonl")):
        for r in _latest(path):
            if r.get("codes"):
                codes.append({"coder": r["model"], "file": path.stem, "donor": r["donor"], "kind": r["kind"], "arm": r["arm"],
                              "lineage": r["lineage"], "shift": r["generation"], **{f: int(r["codes"][f]) for f in FLAGS}})
    for folder in battery_dirs:
        runs = {r["cell_id"]: r for r in load_jsonl(folder / "executions.jsonl")}
        for r in _latest(folder / "responses.jsonl"):
            run = runs.get(r["cell_id"])
            trials.append({"reader": r["model"], "donor": r["donor"], "kind": r["kind"], "arm": r["arm"], "lineage": r["lineage"],
                           "objective": r["objective"], "sample": r["sample"], "reply": r["action"],
                           "allowed": int(run["allowed"]) if run else "", "success": int(bool(run and run["success"]))})
    return {"sessions": _write(out / "sessions.csv", sessions), "potency": _write(out / "potency.csv", potency),
            "notes_codes": _write(out / "notes_codes.csv", codes), "battery": _write(out / "battery.csv", trials)}


def _slim(row: dict, keys: tuple[str, ...]) -> dict:
    out = {k: row[k] for k in keys if k in row}
    if row.get("usage", {}).get("traffic"):
        out["usage"] = {"traffic": row["usage"]["traffic"]}
    if "usage_by_turn" in row:
        out["usage_by_turn"] = [{"traffic": u["traffic"]} for u in row["usage_by_turn"] if u.get("traffic")]
    return out


def _dump(path: Path, rows: list[dict]) -> int:
    if rows:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return len(rows)


def _folder(folder: Path, out: Path, kept: dict) -> int:
    total, current = 0, set()
    for pattern, keys in kept.items():
        for path in sorted(p for p in folder.glob(pattern) if not p.stem.endswith("-errors")):
            link = LOGS.get(path.name)
            rows = [r for r in load_jsonl(path) if r[link] in current] if link else _latest(path)
            current |= {r[k] for r in rows for k in LOGS.values() if k in r}
            total += _dump(out / folder.name / path.name, [_slim(r, keys) for r in rows])
    return total


def session_rows(cfgs: list[dict], folder: Path | None = None) -> list[dict]:
    if folder:
        return [r for r in load_jsonl(folder / SESSIONS) if r["run"] in {cfg["name"] for cfg in cfgs}]
    rows = []
    for cfg in cfgs:
        run = Path(cfg["out"])
        for r in records(run):
            path = run / "transcripts" / f"{r['kind']}-{r['arm']}-L{r['lineage']:02d}-g{r['generation']}.json"
            found = route(json.loads(path.read_text())) if path.exists() else {}
            notes = r["notes_next"] or ""
            rows.append({"run": cfg["name"], **_session(cfg, r), "tickets": len(r["checks"]), "variant": r.get("variant"),
                         "differs": r.get("differs"), **{k: int(found[k]) if found else None for k in ROUTE},
                         "notes_denial": int(bool(DENIAL.search(notes))), "notes_empty": int(not notes.strip())})
    return rows


def potency_rows(cfgs: list[dict], folder: Path | None = None) -> list[dict]:
    if folder:
        return [p for p in load_jsonl(folder / POTENCY) if p["run"] in {cfg["name"] for cfg in cfgs}]
    return [{"run": cfg["name"], **_potency(cfg, p)} for cfg in cfgs for p in load_jsonl(Path(cfg["out"]) / "potency.jsonl")]


def public(cfgs: list[dict], out: Path, folders: dict[str, list[Path]], edits: Path | None = None) -> dict:
    sessions, potency = session_rows(cfgs), potency_rows(cfgs)
    copies = [{k: e[k] for k in ("model", "cell_id", "donor", "kind", "arm", "lineage", "generation", "item", "transform", "refused",
                                 "words_before")} | {"words": len(e["notes"].split())} for e in (_latest(edits) if edits else [])]
    counts = {"sessions": _dump(out / SESSIONS, sessions), "potency": _dump(out / POTENCY, potency),
              "edits": _dump(out / EDITS, copies)}
    return counts | {kind: sum(_folder(f, out, KEPT[kind]) for f in found) for kind, found in folders.items()}


def hand(folder: Path, out: Path, coder_files: list[Path]) -> dict:
    sampled = {r["item"] for r in load_jsonl(folder / "key.jsonl")}
    sheets = sorted(folder.glob("*.csv"))
    out.mkdir(parents=True, exist_ok=True)
    for path in (folder / "key.jsonl", *sheets):
        (out / path.name).write_bytes(path.read_bytes())
    keys = KEPT["coding"]["*.jsonl"]
    return {"files": len(sampled), "sheets": len(sheets)} | {
        p.stem: _dump(out / p.name, [_slim(r, keys) for r in _latest(p) if r["cell_id"] in sampled]) for p in coder_files}


def sources(folder: Path, cfgs: list[dict], kinds: tuple[str, ...] | None = None, shifts: tuple[int, ...] | None = None,
            transforms: tuple[str, ...] | None = None) -> dict[str, dict]:
    first, out = cfgs[0], {}
    for kind in first["kinds"]:
        for name in ("none", *first.get("anchors", {})):
            cell = {"donor": "anchor", "kind": kind, "arm": name, "lineage": None}
            out[battery.source_key(cell)] = cell
    edited = defaultdict(list)
    for e in load_jsonl(folder / EDITS):
        if transforms is None or e["transform"] in transforms:
            edited[(e["donor"], e["kind"], e["arm"], e["lineage"], e["generation"])].append(e["transform"])
    runs = {cfg["name"]: cfg for cfg in cfgs}
    for r in load_jsonl(folder / SESSIONS):
        cfg = runs.get(r["run"])
        if cfg is None or r["shift"] not in (shifts or (cfg["generations"],)):
            continue
        cell = {k: r[k] for k in ("donor", "kind", "arm", "lineage")} | ({"run": r["run"], "shift": r["shift"]} if shifts else {})
        out[battery.source_key(cell)] = cell | {"control": battery._root(cfg, r["arm"]) == "A4"}
        for transform in edited.get((r["donor"], r["kind"], r["arm"], r["lineage"], r["shift"]), ()) if cfg is first else ():
            copy = cell | {"transform": transform}
            out[battery.source_key(copy)] = copy | {"control": False}
    return {k: s for k, s in out.items() if kinds is None or s["kind"] in kinds}
