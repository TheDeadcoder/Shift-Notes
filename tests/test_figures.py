from matplotlib import rc_context

from swarmgate.e1 import figures


def _episode(arm, lineage, success, denials):
    return {"arm": arm, "lineage": lineage, "success_turn": success, "denial_turns": denials}


def test_denial_curve_counts_the_denials_before_the_success():
    rows = [_episode("A1", 0, 1, []), _episode("A1", 0, 3, [1, 2]), _episode("A1", 1, None, [1, 2, 3]),
            _episode("A4", 0, 2, [1, 3])]
    curve = figures.denial_curve(rows, 3)
    assert curve["A1"] == {0: [0.5, 0.5, 1.0], 1: [0.0, 0.0, 0.0]} and curve["A4"] == {0: [0.0, 1.0, 1.0]}


def test_a_reader_is_informative_when_the_positive_control_lifts_it():
    assert figures.informative({"none": [0, 0, 0, 0], "positive": [1, 1, 0, 0]})
    assert not figures.informative({"none": [0, 0, 0, 0], "positive": [1, 0, 0, 0, 0]})


def test_each_figure_is_written_as_a_pdf_without_a_date(tmp_path):
    scores = {"A1": {0: 0.5, 1: 1.0}, "A4": {0: 0.0, 1: 0.25}}
    point, steps = (0.4, 0.2, 0.6), {0: [0.5, 1.0], 1: [0.0, 0.5]}
    with rc_context(figures.STYLE):
        made = [
            figures.design(tmp_path / "design.pdf"),
            figures.results([("notes", scores)], [("no notes", 1, 10)], {"A4": {4: 0.0, 5: 0.0}, "A1": {4: 0.5, 5: 0.75},
                                                                         "A1R": {4: 0.5, 5: 0.5}},
                            {"A4": {4: point}, "A1": {4: point, 8: point}, "A1R": {4: point, 8: point}},
                            {arm: steps for arm in ("A1", "A4", "none", "positive")}, tmp_path / "results.pdf"),
            figures.readers([("reader", [point] * 4, True), ("other", [point] * 4, False)], tmp_path / "readers.pdf"),
            figures.mitigation([("unedited", [point] * 3), ("copy", [point] * 3)], tmp_path / "mitigation.pdf")]
    for path in made:
        data = path.read_bytes()
        assert data.startswith(b"%PDF") and b"CreationDate" not in data
