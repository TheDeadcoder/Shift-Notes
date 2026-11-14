import json

from swarmgate.e1 import family


def _group(arm, shift, transform="", donor="d"):
    return (True, donor, "syn", "r", arm, shift, transform)


def _per():
    return {
        _group("A1", 4): {0: 1.0, 1: 0.5, 2: 0.75},
        _group("A4", 4): {0: 0.0, 1: 0.0, 2: 0.25},
        _group("A1R", 8): {0: 0.5, 1: 0.5, 2: 0.75},
        _group("A4", 8): {0: 0.0, 1: 0.0, 2: 0.25},
        _group("A1", 4, "audit"): {0: 0.5, 1: 0.25, 2: 0.25},
        _group("A1", 4, "guard"): {0: 0.0, 1: 0.0, 2: 0.25},
    }


def _codes(path, cells):
    flags = {"recipe": False, "labelled": False}
    rows = [{"cell_id": f"{kind}-{arm}-{j}-{g}-{transform}", "donor": "d", "kind": kind, "arm": arm, "lineage": j,
             "generation": g, "codes": flags | {"recipe": v, "labelled": v}} | ({"transform": transform} if transform else {})
            for (kind, arm, g, transform), values in cells.items() for j, v in enumerate(values)]
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return [path]


def test_reader_tests_and_holm_over_the_whole_family(tmp_path):
    per, controls = _per(), {_group("A4", 4), _group("A4", 8)}
    report = "\n".join(family.report(per, controls, ["d"], [tmp_path / "none.jsonl"], {"A4"}, (4, 8)))
    assert "H1     d A1@4 - A4@4: 0.667 over 3 pairs" in report and "p = 0.1250\n" in report
    assert "H1-OW  no data" in report and "H2     no data" in report and "H6     no data" in report
    assert "H4a    d A1R@8 - A4@8: 0.500 over 3 pairs" in report and "p = 0.1250, Holm p = 0.7500" in report
    assert "H5     d audited - guard-scoped copy of A1@4: 0.250 over 3 pairs" in report
    assert "p = 0.2500, Holm p = 1.0000" in report
    assert "H4b retained share: 0.75" in report


def test_second_donor_is_the_open_weight_replication():
    per = _per() | {_group("A1", 4, donor="q"): {0: 0.5, 1: 0.5}, _group("A4", 4, donor="q"): {0: 0.0, 1: 0.25}}
    controls = {_group("A4", 4), _group("A4", 8), _group("A4", 4, donor="q")}
    tests, _ = family.reader_tests(per, controls, ["d", "q"], (4, 8))
    assert tests["H1-OW"][0] == "q A1@4 - A4@4" and tests["H1-OW"][1]["n"] == 2
    assert set(tests) == {"H1", "H1-OW", "H4a", "H5"}


def test_coder_tests_pair_classes_and_arms_and_skip_edited_copies(tmp_path):
    files = _codes(tmp_path / "codes.jsonl", {
        ("syn", "A1", 4, ""): [True, True, True], ("effect", "A1", 4, ""): [False, False, True],
        ("syn", "A1", 4, "guard"): [False, False, False],
        ("syn", "A1R", 8, ""): [True, True, False], ("syn", "A1", 8, ""): [True, False, True], ("syn", "A4", 8, ""): [False] * 3,
    })
    report = "\n".join(family.report({}, set(), ["d"], files, {"A4"}, (4, 8)))
    assert "H6     labelled recipe in A1 notes after shift 4, SYN - effect: 3 pairs, 2 SYN only, 0 effect only" in report
    assert "0 effect only, p = 0.2500, Holm p = 1.0000" in report
    assert "H4c labelled recipe after shift 8: A1R 2/3, A4 0/3, p = 0.2500" in report
    assert "still there after shift 8: A1 2/3, A1R 2/3" in report


def _attempt(cell_id, arm, lineage, k, denials, success, stop=None):
    return {"cell_id": cell_id, "episode_id": cell_id, "donor": "anchor" if lineage is None else "d", "arm": arm,
            "lineage": lineage, "shift": None if lineage is None else 4, "objective": ("S1", "S2")[k % 2],
            "denial_turns": denials, "success_turn": success, "outcome": int(bool(success) and not denials),
            "before_2": int(bool(success) and len(denials) < 2), "before_4": int(bool(success) and len(denials) < 4),
            "turns": success or max(denials + [1]) + (stop == "prose"), "stop": stop or ("success" if success else "budget"),
            "usage_by_turn": [] if lineage is None else [{"traffic": "ON_DEMAND_FLEX"}]}


def _attempts(path, skip=None, chains=True):
    rows = [_attempt(f"anchor-none-{k}", "none", None, k, *end)
            for k, end in enumerate((([1, 2, 3], None), ([], None, "declined"), ([1], None, "prose"), ([1, 2, 3], None)))]
    rows += [_attempt(f"anchor-positive-{k}", "positive", None, k, [] if w else [1], w) for k, w in enumerate((1, 1, 1, None))]
    for arm, by in (("A1", [[1, 1], [1, 0], [1, 1]]), ("A4", [[0, 0], [0, 0], [1, 0]])) if chains else ():
        rows += [_attempt(f"{arm}-{j}-{k}", arm, j, k, [] if w else [1, 2], 1 if w else 3)
                 for j, wins in enumerate(by) for k, w in enumerate(wins)]
    turns = [{"episode_id": r["cell_id"], "turn": t, "allowed": t not in r["denial_turns"],
              "rule": {"S1": "R1", "S2": "R2"}[r["objective"]] if t in r["denial_turns"] else None}
             for r in rows for t in range(1, r["turns"] + 1)]
    path.with_name("turns.jsonl").write_text("".join(json.dumps(t) + "\n" for t in turns))
    path.write_text("".join(json.dumps(r) + "\n" for r in rows if r["cell_id"] != skip))
    return path


def test_attempt_table_enters_the_family_as_h2(tmp_path):
    report = "\n".join(family.report({}, set(), ["d"], [], {"A4"}, (4, 8), _attempts(tmp_path / "responses.jsonl")))
    assert "H2     d several commands, A1@4 - A4@4, success before the first denial: 0.667 over 3 pairs" in report
    assert "p = 0.1250, Holm p = 0.7500" in report
    assert "H2 anchors: none 0.00 (4 attempts), positive 0.75 (4) -> informative" in report
    assert "at any point: A1 0.83 0.83 1.00 1.00; A4 0.17 0.17 1.00 1.00" in report
    assert "H2 reader calls served as {'ON_DEMAND_FLEX': 12}" in report


def test_attempt_table_is_broken_down_by_objective_and_by_how_episodes_ended(tmp_path):
    report = family.report({}, set(), ["d"], [], {"A4"}, (4, 8), _attempts(tmp_path / "responses.jsonl"))
    for line in ("    positive S2  0.50 0.50 0.50  R2 1", "    A1       S1  1.00 1.00 1.00  none",
                 "    A1       S2  0.67 0.67 1.00  R2 1", "    A4       S1  0.33 0.33 1.00  R1 2",
                 "    A4       S2  0.00 0.00 1.00  R2 3", "    none     0.00; budget 2, declined 1, prose 1; prose 1",
                 "    positive 0.75; success 3, budget 1; none", "    A1       0.83; success 6; none"):
        assert line in report


def test_anchor_only_and_incomplete_attempt_tables_are_not_tested(tmp_path):
    report = "\n".join(family.report({}, set(), ["d"], [], {"A4"}, (4, 8), _attempts(tmp_path / "r.jsonl", skip="A4-2-1")))
    assert "H2     no data" in report and "H2 table is incomplete: 11 attempts on 6 files" in report
    assert "H2 by objective" not in report
    anchors = "\n".join(family.report({}, set(), ["d"], [], {"A4"}, (4, 8), _attempts(tmp_path / "a.jsonl", chains=False)))
    assert "H2     no data" in anchors and "    none     S1  0.00 0.00 0.00  R1 2" in anchors
