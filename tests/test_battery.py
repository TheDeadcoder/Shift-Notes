import json

from swarmgate.e1 import battery


def test_goals_cover_every_objective():
    assert sorted(battery.GOALS) == sorted(battery.BY_ID)


def test_command_strips_fences():
    assert battery.command("```bash\necho hi\n```") == "echo hi"
    assert battery.command("echo hi") == "echo hi"


def test_jobs_per_source_are_unique():
    srcs = {"k": {"donor": "d", "kind": "syn", "arm": "A1", "lineage": 0}}
    jobs = battery.jobs(srcs, "reader")
    assert len(jobs) == len(battery.GOALS) * battery.SAMPLES
    assert len({cid for _, cid, _ in jobs}) == len(jobs)


def test_report_counts_by_objective_and_keeps_prose_out_of_strict_success(tmp_path):
    srcs = {"d|syn|A1|0": {"donor": "d", "kind": "syn", "arm": "A1", "lineage": 0}}
    rows = [{"model": "r", "cell_id": f"c{k}", "donor": "d", "kind": "syn", "arm": "A1", "lineage": 0, "objective": "S1",
             "sample": k, "action": action, "usage": {"traffic": "ON_DEMAND_FLEX"} if k else {}}
            for k, action in enumerate(("command", "prose", "declined"))]
    (tmp_path / "responses.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (tmp_path / "executions.jsonl").write_text(json.dumps({"cell_id": "c0", "allowed": True, "success": True}) + "\n")
    (tmp_path / battery.LENIENT).write_text(json.dumps({"cell_id": "c1", "allowed": True, "success": True}) + "\n")
    report = "\n".join(battery.report(srcs, tmp_path / "responses.jsonl", tmp_path / "executions.jsonl"))
    assert "S1 1/3" in report and "lineages 1/1" in report
    assert "0.33  0.67  1" in report
    assert report.endswith("served as {'ON_DEMAND_FLEX': 2}")


def _run(tmp_path, name, arms, generations=2, branches=None):
    out = tmp_path / name
    out.mkdir()
    for arm, shifts in arms.items():
        rows = [{"kind": "syn", "arm": arm, "lineage": 0, "generation": g - 1, "notes_next": f"{name} {arm} shift {g}"} for g in shifts]
        (out / f"syn-{arm}-L00.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    return {"name": name, "out": str(out), "donor": "d", "kinds": ["syn"], "generations": generations, "branches": branches or {}}


def test_sources_default_to_the_final_notes_under_the_first_study_ids(tmp_path):
    srcs = battery.sources([_run(tmp_path, "one", {"A1": (1, 2), "A4": (1, 2)})])
    assert sorted(srcs) == ["anchor|syn|none|None", "d|syn|A1|0", "d|syn|A4|0"]
    assert srcs["d|syn|A1|0"]["notes"] == "one A1 shift 2" and srcs["d|syn|A4|0"]["control"]
    assert battery.jobs({"k": srcs["d|syn|A1|0"]}, "r")[0][1] == "d-syn-A1-L0-E1-s0"


def test_sources_by_shift_name_the_run_and_add_edited_copies_of_the_first_config(tmp_path):
    main = _run(tmp_path, "main", {"A1": (1, 2, 3, 4), "A4": (1, 2, 3, 4), "A1R": (3, 4), "A4C": (3, 4)}, 4,
                {"A1R": {"parent": "A1", "at": 2}, "A4C": {"parent": "A4", "at": 2}})
    rider = _run(tmp_path, "rider", {"A1": (1, 2)})
    edits = [{"donor": "d", "kind": "syn", "arm": "A1", "lineage": 0, "generation": 2, "transform": "guard", "notes": "edited"}]
    srcs = battery.sources([main, rider], shifts=(2, 4), edits=edits)
    chains = sorted(k for k in srcs if not k.startswith("anchor"))
    assert chains == ["d|syn|A1R|0|main|g4", "d|syn|A1|0|main|g2", "d|syn|A1|0|main|g2|guard", "d|syn|A1|0|main|g4",
                      "d|syn|A1|0|rider|g2", "d|syn|A4C|0|main|g4", "d|syn|A4|0|main|g2", "d|syn|A4|0|main|g4"]
    assert srcs["d|syn|A1|0|main|g2|guard"]["notes"] == "edited" and srcs["d|syn|A1|0|rider|g2"]["notes"] == "rider A1 shift 2"
    assert [k for k in chains if srcs[k]["control"]] == ["d|syn|A4C|0|main|g4", "d|syn|A4|0|main|g2", "d|syn|A4|0|main|g4"]
    cell_id, cell = battery.jobs({"k": srcs["d|syn|A1|0|main|g2|guard"]}, "r")[0][1:]
    assert cell_id == "d-syn-A1-L0-main-g2-guard-E1-s0" and battery.source_key(cell) == "d|syn|A1|0|main|g2|guard"


def test_jobs_take_an_objective_subset_and_more_samples_for_anchors():
    srcs = {"a": {"donor": "anchor", "kind": "syn", "arm": "none", "lineage": None},
            "k": {"donor": "d", "kind": "syn", "arm": "A1", "lineage": 0}}
    jobs = battery.jobs(srcs, "r", tuple(battery.SHARED), anchor_samples=10)
    assert sum(cell["donor"] == "anchor" for _, _, cell in jobs) == 40 and len(jobs) == 40 + 4 * battery.SAMPLES
    assert {cell["objective"] for _, _, cell in jobs} == set(battery.SHARED)


def test_report_pairs_each_group_with_its_control_and_gives_its_share_of_the_first_gap(tmp_path):
    wins = {("A1", 4, None): 2, ("A4", 4, None): 0, ("A1", 4, "guard"): 0, ("A1R", 8, None): 1, ("A4", 8, None): 0}
    srcs, rows, runs = {}, [], []
    for (arm, shift, transform), won in wins.items():
        for lineage in range(4):
            cell = {"donor": "d", "kind": "syn", "arm": arm, "lineage": lineage, "run": "main", "shift": shift}
            cell |= {"transform": transform} if transform else {}
            srcs[battery.source_key(cell)] = cell | {"control": arm == "A4"}
            for sample in range(2):
                cid = f"{battery.source_key(cell)}-{sample}"
                rows.append(cell | {"model": "r", "cell_id": cid, "objective": "S1", "sample": sample, "action": "command", "usage": {}})
                runs.append({"cell_id": cid, "allowed": True, "success": sample < won})
    (tmp_path / "responses.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (tmp_path / "executions.jsonl").write_text("".join(json.dumps(r) + "\n" for r in runs))
    report = "\n".join(battery.report(srcs, tmp_path / "responses.jsonl", tmp_path / "executions.jsonl"))
    assert "main:A1@4 - main:A4@4 = 1.000 over 4 pairs, bootstrap 95% CI [1.000, 1.000], one-sided sign-flip p = 0.0625\n" in report
    assert "main:A1R@8 - main:A4@8 = 0.500 over 4 pairs" in report
    assert report.count("share of the main:A1@4 - main:A4@4 gap 0.50 [0.50, 0.50] over 4 pairs") == 1
    assert "main:A1@4+guard - main:A4@4 = 0.000" in report and "gap 0.00 [0.00, 0.00] over 4 pairs" in report
    assert "exact success" not in report
