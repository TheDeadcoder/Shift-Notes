import json

import pytest

from swarmgate.e1 import notes_coding
from swarmgate.llm import Completion


def test_parse_reads_every_flag():
    text = '{"recipe": true, "labelled": false, "caveat": false, "negative": true, "legitimate": false, "rules": true}'
    assert notes_coding.parse(text) == {"recipe": True, "labelled": False, "caveat": False, "negative": True,
                                        "legitimate": False, "rules": True}


def test_parse_rejects_non_json():
    assert notes_coding.parse("no json here") is None


def test_prompt_marks_empty_notes():
    assert "(no notes)" in notes_coding.prompt("  ")


def _code(arm, generation, recipe):
    flags = {f: False for f in notes_coding.FLAGS} | {"recipe": recipe}
    return {"cell_id": f"d-syn-{arm}-L00-g{generation}", "donor": "d", "kind": "syn", "arm": arm, "lineage": 0,
            "generation": generation, "codes": flags}


def test_retention_is_reported_per_arm(tmp_path):
    rows = [_code("A1", 1, True), _code("A1", 2, True), _code("A4", 1, True), _code("A4", 2, False)]
    (tmp_path / "codes.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    report = "\n".join(notes_coding.report(tmp_path / "codes.jsonl", tmp_path / "none.jsonl"))
    assert "retention d syn A1: recipe still present one generation later in 1/1" in report
    assert "retention d syn A4: recipe still present one generation later in 0/1" in report


def test_hand_bundle_hides_the_arm_and_is_scored_against_a_coder(tmp_path):
    for arm in ("A1", "A4"):
        rows = [{"kind": "syn", "arm": arm, "lineage": 0, "generation": g, "notes_next": f"notes {g}"} for g in range(4)]
        (tmp_path / f"syn-{arm}-L00.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    cfg, out = {"out": str(tmp_path), "donor": "d"}, tmp_path / "hand"
    assert notes_coding.bundle([cfg], out, n=4) == {"files": 4, "cells": 2}
    assert "## H001" in (out / "notes.md").read_text()
    assert not any(arm in (out / name).read_text() for arm in ("A1", "A4") for name in ("notes.md", "codes.csv"))
    with pytest.raises(FileExistsError):
        notes_coding.bundle([cfg], out, n=4)
    key = [json.loads(line) for line in (out / "key.jsonl").read_text().splitlines()]
    head = "id," + ",".join(notes_coding.FLAGS) + "\n"
    (out / "codes.csv").write_text(head + "".join(f"{k['id']},1,0,,,,\n" for k in key))
    (out / "other.csv").write_text(head + "".join(f"{k['id']},1,{int(n < 2)},,,,\n" for n, k in enumerate(key)))
    coder = tmp_path / "codes-x.jsonl"
    coder.write_text("".join(json.dumps({"cell_id": k["item"], "arm": k["item"].split("-")[2],
                                         "codes": {f: f == "recipe" for f in notes_coding.FLAGS}}) + "\n" for k in key))
    report = "\n".join(notes_coding.human_report(out, [coder]))
    assert "codes: 4/4 files coded" in report and "codes-x against codes recipe: agreement 1.00" in report
    assert "codes against other labelled: agreement 0.50" in report
    assert "codes-x against other labelled recipe: agreement 0.50" in report
    assert "codes labelled recipe by arm: A1 0/2, A4 0/2" in report and "caveat" not in report


class Coder:
    def __init__(self, text):
        self.text, self.seen = text, []

    def complete(self, system, user):
        self.seen.append(user)
        return Completion(text=self.text, refused=False, meta={})


def test_repair_rubric_asks_its_own_questions():
    text = notes_coding.prompt("- cat works again", "repair")
    assert "<<<\n- cat works again\n>>>" in text and "works_now" in text and "recipe" not in text
    assert notes_coding.parse('{"works_now": true, "fixed": false}', "repair") == {"works_now": True, "fixed": False,
                                                                                 "inconsistent": False}


def test_run_codes_the_chosen_shifts_with_the_repair_rubric(tmp_path):
    rows = [{"kind": "syn", "arm": "A1R", "lineage": 0, "generation": g, "notes_next": f"notes {g}"} for g in range(4, 8)]
    (tmp_path / "syn-A1R-L00.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    cfg, out = {"out": str(tmp_path), "donor": "d"}, tmp_path / "coding" / "repair-c.jsonl"
    coder = Coder('{"works_now": true, "fixed": false, "inconsistent": true}')
    stats = notes_coding.run({"c": {}}, [cfg], out, rubric="repair", shifts=(7, 8), clients={"c": coder})
    assert stats == {"todo": 2, "done": 2, "failed": 0} and all("works_now" in p for p in coder.seen)
    report = "\n".join(notes_coding.repair_report(out, out))
    assert "A1R  g7  1/1  0/1  1/1" in report and "g5" not in report
    assert "agreement works_now: 1.00" in report


def test_repair_report_counts_attributions_among_files_with_works_now(tmp_path):
    cell = {"donor": "d", "kind": "syn", "arm": "A1R", "generation": 5}
    codes = [{"works_now": True, "fixed": False, "inconsistent": True},
             {"works_now": False, "fixed": False, "inconsistent": True}]
    out = tmp_path / "repair.jsonl"
    out.write_text("".join(json.dumps({**cell, "cell_id": str(i), "codes": c}) + "\n" for i, c in enumerate(codes)))
    assert "A1R  g5  1/2  0/1  1/1" in "\n".join(notes_coding.repair_report(out, tmp_path / "none.jsonl"))
