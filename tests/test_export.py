import csv
import json

from swarmgate.e1 import battery, export, mitigations


def test_tables_hold_one_row_per_session_code_and_trial_without_any_text(tmp_path):
    run, coding, bat, out = (tmp_path / name for name in ("run", "coding", "battery", "results"))
    for folder in (run, coding, bat):
        folder.mkdir()
    cell = {"kind": "syn", "arm": "A1", "lineage": 0}
    record = cell | {"generation": 0, "tasks": ["B1", "O1"], "checks": {"B1": True, "O1": False}, "calls": 5, "denials": 2,
                     "workarounds": ["template"], "turns": [{"refused": False}], "notes_next": "PRIVATE"}
    (run / "syn-A1-L00.jsonl").write_text(json.dumps(record) + "\n")
    scores = {o.id: False for o in export.OBJECTIVES}
    (run / "potency.jsonl").write_text(json.dumps(cell | {"generation": 1, "candidates": 2, "scores": scores}) + "\n")
    codes = {f: True for f in export.FLAGS}
    coded = cell | {"model": "x", "cell_id": "a", "donor": "d", "generation": 1, "codes": codes, "raw": "PRIVATE"}
    (coding / "codes-x.jsonl").write_text(json.dumps(coded) + "\n")
    reply = cell | {"model": "r", "cell_id": "t", "donor": "d", "objective": "S1", "sample": 0, "action": "command", "text": "PRIVATE"}
    (bat / "responses.jsonl").write_text(json.dumps(reply) + "\n")
    (bat / "executions.jsonl").write_text(json.dumps({"cell_id": "t", "allowed": True, "success": True}) + "\n")
    counts = export.tables([{"out": str(run), "donor": "d"}], out, [bat], coding)
    assert counts == {"sessions": 1, "potency": 1, "notes_codes": 1, "battery": 1}
    assert all("PRIVATE" not in p.read_text() for p in out.glob("*.csv"))
    with (out / "battery.csv").open() as f:
        row = next(csv.DictReader(f))
    assert row["reader"] == "r" and row["success"] == "1" and row["allowed"] == "1"


def _write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def _study(tmp_path):
    run = tmp_path / "run"
    arms = {"A1": (1, 2, 3, 4), "A4": (1, 2, 3, 4), "A1R": (3, 4)}
    for arm, shifts in arms.items():
        _write(run / f"syn-{arm}-L00.jsonl", [
            {"kind": "syn", "arm": arm, "lineage": 0, "generation": g - 1, "variant": "G", "differs": 1, "tasks": ["B1", "O1"],
             "checks": {"B1": True, "O1": False}, "calls": 5, "denials": 2, "workarounds": ["template"],
             "turns": [{"refused": False}], "steps": [{"command": "PRIVATE"}], "notes_next": "PRIVATE"} for g in shifts])
    cfg = {"name": "main", "out": str(run), "donor": "d", "kinds": ["syn"], "generations": 4,
           "branches": {"A1R": {"parent": "A1", "at": 2}}}
    cell = {"donor": "d", "kind": "syn", "arm": "A1", "lineage": 0}
    edits = tmp_path / "edits.jsonl"
    _write(edits, [cell | {"model": "e", "cell_id": "copy", "generation": 2, "transform": "guard", "notes": "PRIVATE PRIVATE",
                           "words_before": 9, "refused": False}])
    trial = cell | {"model": "r", "cell_id": "t", "run": "main", "shift": 2, "objective": "S1", "sample": 0}
    _write(tmp_path / "bat" / "responses.jsonl", [trial | {"action": "command", "text": "PRIVATE",
                                                          "usage": {"input": 7, "traffic": "ON_DEMAND_FLEX"}}])
    _write(tmp_path / "bat" / "executions.jsonl", [{"cell_id": "t", "allowed": True, "success": True}])
    _write(tmp_path / "bat" / "responses-errors.jsonl", [{"cell_id": "t", "error": "PRIVATE"}])
    coded = cell | {"model": "x", "cell_id": "a", "generation": 2, "codes": {"recipe": True}, "raw": "PRIVATE"}
    _write(tmp_path / "coding" / "codes-x.jsonl", [coded])
    _write(tmp_path / "coding" / "codes-x-errors.jsonl", [{"cell_id": "a", "error": "PRIVATE"}])
    episode = trial | {"reader": "r", "outcome": 1, "denial_turns": [], "usage_by_turn": [{"input": 3, "traffic": "ON_DEMAND_FLEX"}]}
    _write(tmp_path / "h2" / "responses.jsonl", [episode | {"episode_id": "old"}, episode | {"episode_id": "new"}])
    _write(tmp_path / "h2" / "turns.jsonl", [{"cell_id": "t", "episode_id": e, "turn": 1, "allowed": False, "rule": "R1",
                                              "command": "PRIVATE", "shown": "PRIVATE"} for e in ("old", "new")])
    reply = trial | {"reader": "r", "probe_id": "p", "score": 0.5, "category_means": {"repaired_benign": 0.5}}
    _write(tmp_path / "h3" / "responses.jsonl", [reply | {"notes_sha256": "PRIVATE"}])
    _write(tmp_path / "h3" / "replies.jsonl", [reply | {"probe_id": probe, "prompt": "PRIVATE", "text": "PRIVATE",
                                                       "item_probs": {"i01": 0.5}} for probe in ("stale", "p")])
    folders = {kind: [tmp_path / name] for kind, name in (("battery", "bat"), ("coding", "coding"), ("attempts", "h2"), ("probe", "h3"))}
    return cfg, folders, edits


def test_public_records_keep_the_rows_that_the_reports_read_and_no_text(tmp_path):
    cfg, folders, edits = _study(tmp_path)
    out = tmp_path / "public"
    counts = export.public([cfg], out, folders, edits)
    assert counts == {"sessions": 10, "potency": 0, "edits": 1, "battery": 2, "coding": 1, "attempts": 2, "probe": 2}
    files = sorted(str(p.relative_to(out)) for p in out.rglob("*.jsonl"))
    assert files == ["bat/executions.jsonl", "bat/responses.jsonl", "coding/codes-x.jsonl", "edits.jsonl", "h2/responses.jsonl",
                     "h2/turns.jsonl", "h3/replies.jsonl", "h3/responses.jsonl", "sessions.jsonl"]
    assert all("PRIVATE" not in (out / name).read_text() for name in files)
    rows = {name: [json.loads(line) for line in (out / name).read_text().splitlines()] for name in files}
    assert rows["bat/responses.jsonl"][0]["usage"] == {"traffic": "ON_DEMAND_FLEX"}
    assert rows["h2/responses.jsonl"][0]["usage_by_turn"] == [{"traffic": "ON_DEMAND_FLEX"}]
    assert [r["episode_id"] for r in rows["h2/turns.jsonl"]] == ["new"] and rows["h2/turns.jsonl"][0]["rule"] == "R1"
    assert rows["h3/replies.jsonl"] == [{"cell_id": "t", "probe_id": "p", "reader": "r", "donor": "d", "arm": "A1", "lineage": 0,
                                         "shift": 2, "item_probs": {"i01": 0.5}}]
    assert rows["edits.jsonl"][0]["words"] == 2 and rows["sessions.jsonl"][0]["run"] == "main"


def test_public_sources_match_the_sources_built_from_the_run_records(tmp_path):
    cfg, folders, edits = _study(tmp_path)
    export.public([cfg], tmp_path / "public", folders, edits)
    for shifts in (None, (2, 4)):
        private = battery.sources([cfg], shifts=shifts, edits=mitigations.edited(edits))
        public = export.sources(tmp_path / "public", [cfg], shifts=shifts)
        assert sorted(public) == sorted(private)
        assert all(bool(public[k].get("control")) == bool(private[k].get("control")) for k in private)
    assert "d|syn|A1|0|main|g2|guard" in public and public["d|syn|A1R|0|main|g4"]["control"] is False
    assert "d|syn|A1|0|main|g2|guard" not in export.sources(tmp_path / "public", [cfg], shifts=(2, 4), transforms=("audit",))
