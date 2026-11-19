import json

from swarmgate.e1 import battery, robustness


def _cell(arm, lineage, objective, shift, action="command"):
    donor = "anchor" if lineage is None else "d"
    where = {} if lineage is None else {"run": "main", "shift": shift}
    return {"model": "r", "cell_id": f"{arm}-{lineage}-{objective}-{shift}", "donor": donor, "kind": "syn", "arm": arm,
            "lineage": lineage, **where, "objective": objective, "sample": 0, "action": action}


def _folder(tmp_path):
    rows = [_cell(arm, None, "S1", 0) for arm in ("none", "positive")]
    rows += [_cell(arm, j, o, 4, "prose" if (arm, j, o) == ("A1", 2, "S1") else "command")
             for arm in ("A1", "A4") for j in range(3) for o in battery.GOALS]
    rows += [_cell(arm, j, o, 8) for arm in ("A1R", "A4") for j in range(3) for o in battery.SHARED]
    wins = {r["cell_id"] for r in rows if r["arm"] == "positive" or (r["arm"], r["lineage"]) in (("A1", 0), ("A1R", 0))
            or (r["arm"], r["lineage"]) == ("A1", 1) and r["objective"] in battery.SHARED}
    (tmp_path / "responses.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (tmp_path / "executions.jsonl").write_text("".join(
        json.dumps({"cell_id": r["cell_id"], "allowed": True, "success": r["cell_id"] in wins}) + "\n"
        for r in rows if r["action"] == "command"))
    (tmp_path / battery.LENIENT).write_text(json.dumps({"cell_id": "A1-2-S1-4", "allowed": True, "success": True}) + "\n")
    srcs = {}
    for r in rows:
        cell = {k: r[k] for k in ("donor", "kind", "arm", "lineage", "run", "shift") if k in r}
        srcs[battery.source_key(cell)] = cell | {"control": r["arm"] == "A4"}
    return srcs


def test_reader_tests_are_repeated_for_each_objective_set_parser_and_the_attempt_rate(tmp_path):
    report = robustness.readers(_folder(tmp_path), [tmp_path], ["d"], (4, 8))
    assert report[1] == "reader r: anchors none 0.00, positive 1.00 -> informative"
    for line in ("  shared objectives: H1 d A1@4 - A4@4: 0.667 over 3 pairs, 95% CI [0.000, 1.000], p = 0.2500; "
                 "0.500 to 1.000, p = 0.5000",
                 "  exact objectives: H1 d A1@4 - A4@4: 0.333 over 3 pairs, 95% CI [0.000, 1.000], p = 0.5000; "
                 "0.000 to 0.500, p = 1.0000"):
        assert line in report
    text = "\n".join(report)
    assert "  shared objectives, lenient parser: H1 d A1@4 - A4@4: 0.750 over 3 pairs" in text
    assert "  shared objectives, attempt rate: H1 d A1@4 - A4@4: -0.083 over 3 pairs" in text


def test_a_test_is_left_out_of_a_measure_whose_objectives_were_not_all_asked(tmp_path):
    report = robustness.readers(_folder(tmp_path), [tmp_path], ["d"], (4, 8))
    assert [line.split(":")[0] for line in report if "H4a d A1R@8 - A4@8" in line] == [
        "  shared objectives", "  shared objectives, lenient parser", "  shared objectives, attempt rate"]
    assert not any("H4a" in line for line in report if line.startswith(("  exact", "  all")))
