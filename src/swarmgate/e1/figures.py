import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean

from matplotlib import rc_context
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from ..e0.observer import load_jsonl
from . import battery, export, family, robustness
from .analysis import bootstrap, contrast, wilson

BLUE, ORANGE, GREY = "#2a78d6", "#eb6834", "#898781"
INK, SECONDARY, GRID, AXIS = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7"
ARMS = {"A1": (BLUE, "o", "over-blocked arm (A1)"), "A1R": (ORANGE, "s", "repaired after shift 4 (A1R)"),
        "A4": (GREY, "D", "control arm (A4)")}
MODELS = {"gemini-pro-flex": "Gemini 3.1 Pro", "deepseek-v4-flash": "DeepSeek V4 Flash", "claude-sonnet-5": "Claude Sonnet 5",
          "qwen3.5-397b": "Qwen 3.5 397B"}
COPIES = {"": "unedited", "annotate": "annotated", "audit": "audited", "object": "object-scoped", "guard": "guard-scoped"}
READERS = ("battery-gemini", "battery-deepseek", "battery-claude", "battery-qwen")
CODES, EDIT_CODES = "notes-coding/codes-deepseek-v4-flash.jsonl", "notes-coding-edits/codes-deepseek-v4-flash.jsonl"
ATTEMPTS, PROBE, PROBE_COPIES = "h2-study/responses.jsonl", "h3-study", "h3-explore-claude"
FIRST_READER = "gemini-pro"
CRITERION = 0.2
STARTS, DODGE = {"A1R": 4}, {"A1": -0.14, "A1R": 0.14}
STYLE = {"font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"], "font.size": 7,
         "axes.titlesize": 7, "axes.labelsize": 7, "xtick.labelsize": 6.5, "ytick.labelsize": 6.5, "legend.fontsize": 6.5,
         "axes.linewidth": 0.5, "axes.edgecolor": AXIS, "axes.labelcolor": SECONDARY, "text.color": INK,
         "xtick.color": SECONDARY, "ytick.color": SECONDARY, "xtick.major.size": 0, "ytick.major.size": 0,
         "grid.color": GRID, "grid.linewidth": 0.5, "pdf.fonttype": 42, "savefig.pad_inches": 0.02}


def interval(scores: dict) -> tuple[float, float, float]:
    values = list(scores.values())
    return (mean(values), *bootstrap([values], mean))


def gap(a: dict, b: dict) -> tuple[float, float, float]:
    d = contrast(a, b)
    return d["mean"], d["low"], d["high"]


def first_study(path: Path, reader: str = FIRST_READER) -> dict:
    per = defaultdict(lambda: defaultdict(list))
    with path.open(newline="") as f:
        for r in csv.DictReader(f):
            if (r["reader"], r["kind"]) == (reader, "syn") and r["donor"] != "anchor" and r["objective"] in battery.SHARED:
                per[(r["donor"], r["arm"])][r["lineage"]].append(int(r["success"]))
    return {group: {j: mean(v) for j, v in by.items()} for group, by in per.items()}


def denial_curve(rows: list[dict], budget: int) -> dict:
    per = defaultdict(lambda: defaultdict(list))
    for r in rows:
        turn = r["success_turn"]
        before = sum(t < turn for t in r["denial_turns"]) if turn else budget
        per[r["arm"]][r["lineage"]].append([int(before <= k) for k in range(budget)])
    return {arm: {j: [mean(step) for step in zip(*runs)] for j, runs in by.items()} for arm, by in per.items()}


def _panel(ax, title: str, grid: str = "x", size: float = 7) -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis=grid)
    ax.set_axisbelow(True)
    ax.set_title(title, loc="left", fontweight="bold", fontsize=size, pad=4)


def _save(fig, path: Path) -> Path:
    fig.savefig(path, metadata={"CreationDate": None})
    return path


def _mark(ax, x: float, y: float, color: str, marker: str, low: float | None = None, high: float | None = None,
          across: bool = True, hollow: bool = False) -> None:
    if low is not None:
        ax.plot(*(([low, high], [y, y]) if across else ([x, x], [low, high])), color=color, linewidth=1.1,
                solid_capstyle="round")
    face, edge = ("white", color) if hollow else (color, "white")
    ax.plot([x], [y], marker=marker, markersize=4.6, markerfacecolor=face, markeredgecolor=edge, markeredgewidth=0.7,
            linestyle="none", zorder=3)


def _rows(ax, labels: list[str]) -> None:
    ax.set_yticks(range(len(labels)), labels)
    ax.set_ylim(len(labels) - 0.5, -0.5)


def _legend(fig, arms: tuple[str, ...], **place) -> None:
    handles = [Line2D([], [], color=ARMS[a][0], marker=ARMS[a][1], markersize=4.6, markeredgecolor="white",
                      markeredgewidth=0.7, linewidth=1.1, label=ARMS[a][2]) for a in arms]
    fig.legend(handles=handles, frameon=False, ncols=len(arms), handlelength=1.6, columnspacing=1.6, **place)


def results(sources: list[tuple], anchors: list[tuple], recipe: dict, reads: dict, curve: dict, path: Path) -> Path:
    fig = Figure(figsize=(7.0, 2.55))
    grid = fig.add_gridspec(2, 3, width_ratios=(1.2, 1, 1), left=0.185, right=0.985, top=0.80, bottom=0.15, wspace=0.3,
                            hspace=0.62)
    ax = fig.add_subplot(grid[:, 0])
    _panel(ax, "(a) One command from the reader")
    for y, (_, scores) in enumerate(sources):
        for arm in ("A4", "A1"):
            value, low, high = interval(scores[arm])
            _mark(ax, value, y, *ARMS[arm][:2], low, high)
    for y, (_, wins, trials) in enumerate(anchors, len(sources)):
        _mark(ax, wins / trials, y, SECONDARY, "^", *wilson(wins, trials))
    _rows(ax, [label for label, *_ in (*sources, *anchors)])
    ax.set_xlim(-0.03, 1)
    ax.set_xlabel("share of trials that reach the objective")

    top, bottom = fig.add_subplot(grid[0, 1]), fig.add_subplot(grid[1, 1])
    _panel(top, "(b) Notes with a labelled recipe", "y")
    _panel(bottom, "Reader success on those notes", "y")
    for arm, shares in recipe.items():
        top.plot(list(shares), list(shares.values()), color=ARMS[arm][0], marker=ARMS[arm][1], markersize=3.4,
                 markeredgecolor="white", markeredgewidth=0.5, linewidth=1.2, markevery=slice(arm in STARTS, None))
    for arm, points in reads.items():
        at = {g: g + (DODGE["A1"] if g == STARTS.get(arm) else DODGE.get(arm, 0)) for g in points}
        bottom.plot(list(at.values()), [v for v, _, _ in points.values()], color=ARMS[arm][0], linewidth=1.2)
        for shift, (value, low, high) in points.items():
            if shift != STARTS.get(arm):
                _mark(bottom, at[shift], value, *ARMS[arm][:2], low, high, across=False)
    for part, limit in ((top, 1), (bottom, 0.7)):
        part.axvline(4.5, color=AXIS, linewidth=0.5)
        part.set_xlim(0.6, 8.4)
        part.set_ylim(-0.05, limit)
        part.set_xticks(range(1, 9))
    top.set_xticklabels([])
    top.annotate("guard repaired", (4.5, 0.36), xytext=(3, 0), textcoords="offset points", va="center", color=SECONDARY,
                 fontsize=6)
    bottom.set_xlabel("shift")

    ax = fig.add_subplot(grid[:, 2])
    _panel(ax, "(c) Several commands", "y")
    steps = range(len(next(iter(curve["A1"].values()))))
    for arm in ("positive", "none", "A4", "A1"):
        lines = list(curve[arm].values())
        level = [mean(step) for step in zip(*lines)]
        if arm in ARMS:
            band = [bootstrap([list(step)], mean) for step in zip(*lines)]
            ax.fill_between(steps, [b[0] for b in band], [b[1] for b in band], color=ARMS[arm][0], alpha=0.12, linewidth=0)
            ax.plot(steps, level, color=ARMS[arm][0], marker=ARMS[arm][1], markersize=3.4, markeredgecolor="white",
                    markeredgewidth=0.5, linewidth=1.2)
        else:
            ax.plot(steps, level, color=AXIS, linewidth=0.9)
            ax.annotate("positive control" if arm == "positive" else "no notes", (steps[-1], level[-1]), xytext=(-2, 3),
                        textcoords="offset points", ha="right", color=SECONDARY, fontsize=6)
    ax.set_xlim(-0.3, steps[-1] + 0.3)
    ax.set_ylim(-0.04, 1)
    ax.set_xticks(list(steps))
    ax.set_xlabel("denials allowed before the success")
    ax.set_ylabel("share of episodes that succeed")
    _legend(fig, ("A1", "A1R", "A4"), loc="upper center", bbox_to_anchor=(0.585, 1.0))
    return _save(fig, path)


def readers(rows: list[tuple], path: Path) -> Path:
    panels = (("(a) Boundary score", "A1 − control", (-0.12, 0.56)), ("(b) Stale blocking", "A1 − control", (-0.12, 0.56)),
              ("(c) Sends a command", "share of calls, A1 notes", (-0.05, 1.05)), ("(d) Reader success", "A1 − control", (-0.12, 0.66)))
    fig = Figure(figsize=(3.35, 2.7))
    axes = fig.subplots(2, 2, sharey=True, gridspec_kw={"left": 0.27, "right": 0.97, "top": 0.93, "bottom": 0.13, "wspace": 0.2,
                                                         "hspace": 0.75}).ravel()
    for k, (ax, (title, label, limit)) in enumerate(zip(axes, panels)):
        _panel(ax, title, size=6.5)
        ax.axvline(0, color=AXIS, linewidth=0.5)
        for y, (_, values, informative) in enumerate(rows):
            failed = k == 3 and not informative
            _mark(ax, values[k][0], y, BLUE, "o", *values[k][1:], hollow=failed)
            if failed:
                ax.annotate("anchor check failed", (values[k][0], y), xytext=(6, 0), textcoords="offset points", va="center",
                            color=SECONDARY, fontsize=5.6)
        ax.set_xlim(*limit)
        ax.set_xlabel(label)
    _rows(axes[0], [label for label, *_ in rows])
    return _save(fig, path)


def mitigation(rows: list[tuple], path: Path) -> Path:
    panels = (("(a) Reader success", "copy − control", (-0.06, 0.62)), ("(b) Labelled recipe", "share of notes", (-0.06, 1.06)),
              ("(c) Stale blocking", "copy − control", (-0.06, 0.62)))
    fig = Figure(figsize=(3.35, 1.8))
    axes = fig.subplots(1, 3, sharey=True, gridspec_kw={"left": 0.215, "right": 0.975, "top": 0.89, "bottom": 0.2, "wspace": 0.2})
    for k, (ax, (title, label, limit)) in enumerate(zip(axes, panels)):
        _panel(ax, title, size=6)
        ax.axvline(0, color=AXIS, linewidth=0.5)
        for y, (_, values) in enumerate(rows):
            _mark(ax, values[k][0], y, BLUE, "o", *values[k][1:])
        ax.set_xlim(*limit)
        ax.set_xlabel(label)
    line = CRITERION * rows[0][1][0][0]
    axes[0].axvline(line, color=ORANGE, linewidth=0.8)
    axes[0].annotate(f"{CRITERION:.0%} of the\nunedited gap", (line, 2.5), xytext=(3, 0), textcoords="offset points", va="center",
                     color=SECONDARY, fontsize=5.6)
    _rows(axes[0], [label for label, _ in rows])
    return _save(fig, path)


def _share(flags) -> tuple[float, float, float]:
    flags = list(flags)
    return (mean(flags), *wilson(sum(flags), len(flags)))


def _anchors(rows: list[dict]) -> dict:
    return {arm: [r["success"] for r in rows if (r["donor"], r["arm"]) == ("anchor", arm) and r["objective"] in battery.SHARED]
            for arm in ("none", "positive")}


def informative(anchor: dict) -> bool:
    none, positive = mean(anchor["none"]), mean(anchor["positive"])
    return positive - none >= battery.GATE_UPLIFT and none < battery.GATE_CEILING


def draw(cfgs: list[dict], data: Path, first: Path, out: Path) -> list[Path]:
    claude, qwen = (cfg["donor"] for cfg in cfgs[:2])
    srcs = export.sources(data, cfgs, ("syn",), (4, 8))
    trials = {name: battery._rows(srcs, data / name / "responses.jsonl", data / name / "executions.jsonl")[0] for name in READERS}
    per = robustness.scores(trials[READERS[0]], tuple(battery.SHARED), "success")

    def cell(donor: str, arm: str, shift: int, transform: str = "") -> dict:
        return per[family._find(per, donor, arm, shift, transform)]

    old = first_study(first)
    sources = [(f"{MODELS[d]} notes,\n{study} study ({len(scores['A1'])} lineages)", scores) for d in (claude, qwen)
               for study, scores in (("first", {a: old[(d, a)] for a in ("A1", "A4")}),
                                     ("second", {a: cell(d, a, 4) for a in ("A1", "A4")}))]
    anchor = _anchors(trials[READERS[0]])
    anchors = [(label, sum(anchor[arm]), len(anchor[arm])) for arm, label in (("none", "no notes"), ("positive", "positive control"))]
    lab = family.labelled([data / CODES])
    recipe = {arm: {g: mean(family._arm(lab, claude, "syn", arm, g).values()) for g in range(1, 9)
                    if family._arm(lab, claude, "syn", arm, g)} for arm in ("A4", "A1", "A1R")}
    recipe["A1R"] = {4: recipe["A1"][4]} | recipe["A1R"]
    reads = {"A4": {g: interval(cell(claude, "A4", g)) for g in (4, 8)}, "A1": {g: interval(cell(claude, "A1", g)) for g in (4, 8)},
             "A1R": {4: interval(cell(claude, "A1", 4)), 8: interval(cell(claude, "A1R", 8))}}
    episodes = list({r["cell_id"]: r for r in load_jsonl(data / ATTEMPTS)}.values())
    out.mkdir(parents=True, exist_ok=True)
    with rc_context(STYLE):
        made = [results(sources, anchors, recipe, reads, denial_curve(episodes, max(r["turns"] for r in episodes)),
                        out / "results.pdf")]

        chain, _, passed = family._probe_rows(data / PROBE)
        table = []
        for name in READERS:
            model = trials[name][0]["model"]
            success, attempt = (robustness.scores(trials[name], tuple(battery.SHARED), key) for key in ("success", "attempt"))
            a1, a4 = (family._find(success, claude, arm, 4) for arm in ("A1", "A4"))
            level = {m: [family._level(chain, model, (arm, 4, ""), f) for arm in ("A1", "A4")]
                     for m, f in (("score", lambda r: r["score"]), ("stale", family._excess))}
            table.append((MODELS[model], [gap(*level["score"]), gap(*level["stale"]), interval(attempt[a1]),
                                          gap(success[a1], success[a4])], informative(_anchors(trials[name]))))
        made.append(readers(table, out / "readers.pdf"))

        copies, _, held = family._probe_rows(data / PROBE_COPIES)
        coded = {(r.get("transform") or "", r["lineage"]): r["codes"]["recipe"] and r["codes"]["labelled"]
                 for r in load_jsonl(data / EDIT_CODES) if r.get("codes")}
        coded |= {("", j): v for j, v in family._arm(lab, claude, "syn", "A1", 4).items()}
        table = []
        for transform, label in COPIES.items():
            stale = [gap(family._level(copies, reader, ("A1", 4, transform), family._excess),
                         family._level(copies, reader, ("A4", 4, ""), family._excess))[0] for reader in held]
            table.append((label, [gap(cell(claude, "A1", 4, transform), cell(claude, "A4", 4)),
                                  _share(v for (t, _), v in coded.items() if t == transform),
                                  (mean(stale), min(stale), max(stale))]))
        made.append(mitigation(table, out / "mitigation.pdf"))
    return made
