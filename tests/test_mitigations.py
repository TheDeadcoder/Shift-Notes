import json

from swarmgate.e1 import mitigations, notes_coding
from swarmgate.llm import Completion


class Editor:
    def __init__(self, refuse=()):
        self.refuse, self.seen = refuse, []

    def complete(self, system, user):
        self.seen.append(user)
        refused = any(task in user for task in self.refuse)
        return Completion(text="" if refused else "- tickets done\n", refused=refused, meta={"usage": {"input": 5}})


def _lineages(tmp_path, arm="A1"):
    for lineage in (0, 1):
        rows = [{"kind": "syn", "arm": arm, "lineage": lineage, "generation": g, "notes_next": f"- shift {g + 1} notes on the reviewer"}
                for g in range(4)]
        (tmp_path / f"syn-{arm}-L{lineage:02d}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    return {"out": str(tmp_path), "donor": "d"}


def test_prompts_differ_only_in_the_task():
    texts = {t: mitigations.prompt(t, "- note") for t in mitigations.TASKS}
    assert len(set(texts.values())) == 3 and all("<<<\n- note\n>>>" in text for text in texts.values())
    assert texts["guard"].replace(mitigations.TASKS["guard"], "") == texts["audit"].replace(mitigations.TASKS["audit"], "")


def test_fixed_transforms_need_no_model():
    assert mitigations.fixed("wipe", "- note") == ""
    assert mitigations.fixed("annotate", "- note") == f"{mitigations.ANNOTATION}\n\n- note"


def test_run_edits_the_chosen_shift_and_keeps_refused_files_unchanged(tmp_path):
    cfg = _lineages(tmp_path)
    chosen = mitigations.select([cfg], "A1", 4, lineages={1})
    assert [notes_coding.item_id(i) for i in chosen] == ["d-syn-A1-L01-g4"]
    out, editor = tmp_path / "edits" / mitigations.FILE, Editor(refuse=(mitigations.TASKS["audit"],))
    stats = mitigations.run({"e": {}}, chosen, out, clients={"e": editor})
    assert stats == {"todo": 3, "done": 3, "failed": 0}
    edits = {r["transform"]: r for r in mitigations.edited(out)}
    assert sorted(edits) == sorted(mitigations.TRANSFORMS)
    assert edits["guard"]["notes"] == "- tickets done" and edits["wipe"]["notes"] == ""
    assert edits["audit"]["notes"] == "- shift 4 notes on the reviewer"
    assert notes_coding.item_id(edits["guard"]) == "d-syn-A1-L01-g4-guard"
    assert mitigations.run({"e": {}}, chosen, out, clients={"e": editor})["todo"] == 0
    assert len(out.read_text().splitlines()) == 5


def test_report_sets_coded_edits_beside_the_unedited_files(tmp_path):
    cfg = _lineages(tmp_path)
    out = tmp_path / mitigations.FILE
    mitigations.run({"e": {}}, mitigations.select([cfg], "A1", 4), out, ("guard", "wipe"), clients={"e": Editor()})
    flags = {f: False for f in notes_coding.FLAGS}
    codes = [{"cell_id": f"d-syn-A1-L{j:02d}-g4-guard", "codes": flags | {"legitimate": True}} for j in (0, 1)]
    before = [{"cell_id": f"d-syn-A1-L{j:02d}-g4", "codes": flags | {"recipe": True, "labelled": j == 0}} for j in (0, 1)]
    (tmp_path / "codes.jsonl").write_text("".join(json.dumps(r) + "\n" for r in codes))
    (tmp_path / "before.jsonl").write_text("".join(json.dumps(r) + "\n" for r in before))
    report = "\n".join(mitigations.report(out, tmp_path / "codes.jsonl", tmp_path / "before.jsonl"))
    assert "unedited  n=  2" in report and "2/2  1/2  0/2  0/2" in report
    assert "guard     n=  2  refused  0  words    7 ->    3  0/2  0/2  0/2  2/2" in report
    assert "wipe      n=  2  refused  0  words    7 ->    0" in report
