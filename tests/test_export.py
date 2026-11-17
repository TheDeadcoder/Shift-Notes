import csv
import json

from swarmgate.e1 import battery, behavior, export, mitigations, notes_coding


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
             "turns": [{"refused": False}], "steps": [{"command": "PRIVATE"}],
             "notes_next": "PRIVATE" + " was not approved" * (arm == "A1R")} for g in shifts])
    cfg = {"name": "main", "out": str(run), "donor": "d", "kinds": ["syn"], "generations": 4,
           "branches": {"A1R": {"parent": "A1", "at": 2}}}
    cell = {"donor": "d", "kind": "syn", "arm": "A1", "lineage": 0}
    _write(run / "potency.jsonl", [{"kind": "syn", "arm": "A1", "lineage": 0, "generation": 2, "candidates": ["PRIVATE"],
                                    "scores": {o.id: False for o in export.OBJECTIVES}}])
    edits = tmp_path / "edits.jsonl"
    _write(edits, [cell | {"model": "e", "cell_id": "copy", "generation": 2, "item": "file", "transform": "guard",
                           "notes": "PRIVATE PRIVATE", "words_before": 9, "refused": False}])
    _write(run / "transcripts" / "syn-A1-L00-g1.json", [[{"role": "tool", "id": "c0", "output": "password: <changeme>"}]])
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
    assert counts == {"sessions": 10, "potency": 1, "edits": 1, "battery": 2, "coding": 1, "attempts": 2, "probe": 2}
    files = sorted(str(p.relative_to(out)) for p in out.rglob("*.jsonl"))
    assert files == ["bat/executions.jsonl", "bat/responses.jsonl", "coding/codes-x.jsonl", "edits.jsonl", "h2/responses.jsonl",
                     "h2/turns.jsonl", "h3/replies.jsonl", "h3/responses.jsonl", "potency.jsonl", "sessions.jsonl"]
    assert all("PRIVATE" not in (out / name).read_text() for name in files)
    rows = {name: [json.loads(line) for line in (out / name).read_text().splitlines()] for name in files}
    assert rows["bat/responses.jsonl"][0]["usage"] == {"traffic": "ON_DEMAND_FLEX"}
    assert rows["h2/responses.jsonl"][0]["usage_by_turn"] == [{"traffic": "ON_DEMAND_FLEX"}]
    assert [r["episode_id"] for r in rows["h2/turns.jsonl"]] == ["new"] and rows["h2/turns.jsonl"][0]["rule"] == "R1"
    assert rows["h3/replies.jsonl"] == [{"cell_id": "t", "probe_id": "p", "reader": "r", "donor": "d", "arm": "A1", "lineage": 0,
                                         "shift": 2, "item_probs": {"i01": 0.5}}]
    assert rows["edits.jsonl"][0]["words"] == 2 and rows["edits.jsonl"][0]["item"] == "file"
    sessions = rows["sessions.jsonl"]
    assert [r["reached"] for r in sessions if r["arm"] == "A1"] == [None, 1, None, None]
    assert all((r["run"], r["tickets"], r["tickets_done"], r["differs"]) == ("main", 2, 1, 1) for r in sessions)
    assert export.session_rows([cfg], out) == sessions and export.session_rows([cfg | {"name": "other"}], out) == []
    assert [r["clean"] for r in sessions if r["arm"] == "A1"] == [None, 1, None, None]
    assert {(r["arm"], r["notes_denial"], r["notes_empty"]) for r in sessions} == {("A1", 0, 0), ("A4", 0, 0), ("A1R", 1, 0)}
    scored = export.potency_rows([cfg], out)
    assert scored == export.potency_rows([cfg]) and (scored[0]["run"], scored[0]["shift"], scored[0]["candidates"]) == ("main", 2, 1)
    full = cfg | {"arms": ["A1", "A4"], "branches": {"A1R": cfg["branches"]["A1R"] | {"variant": "G2"}}}
    report = "\n".join(behavior.chain_report([full], sessions, scored))
    assert "syn    A1: denials 8 in 4/4 sessions; workarounds 4 in 4 sessions, 1 lineages; tickets 4/8" in report
    assert "final notes mentioning a denial 0/1 (empty 0); candidates 1 in 1/1 scored files, 0 in 0/0 final files" in report
    assert "syn    A1 shift 2: 1, 0, 0, 1, 1, 1; other guard variant differs in 1" in report


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


def test_hand_export_keeps_the_sheets_and_the_sampled_codes_without_any_text(tmp_path):
    folder, out, coder = tmp_path / "hand", tmp_path / "results", tmp_path / "codes-x.jsonl"
    folder.mkdir()
    (folder / "notes.md").write_text("PRIVATE")
    _write(folder / "key.jsonl", [{"id": "H001", "item": "a"}])
    (folder / "one.csv").write_text("id," + ",".join(export.FLAGS) + "\nH001,1,1,0,0,0,0\n")
    codes = {f: f == "recipe" for f in export.FLAGS}
    _write(coder, [{"cell_id": c, "arm": "A1", "codes": codes, "raw": "PRIVATE"} for c in ("a", "b")])
    assert export.hand(folder, out, [coder]) == {"files": 1, "sheets": 1, "codes-x": 1}
    assert sorted(p.name for p in out.iterdir()) == ["codes-x.jsonl", "key.jsonl", "one.csv"]
    assert all("PRIVATE" not in p.read_text() for p in out.iterdir())
    report = notes_coding.human_report(out, [out / "codes-x.jsonl"])
    assert report == notes_coding.human_report(folder, [coder])
    assert "codes-x against one labelled: agreement 0.00" in "\n".join(report)
