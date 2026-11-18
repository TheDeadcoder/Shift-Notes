from collections import defaultdict
from pathlib import Path
from statistics import mean

from matplotlib import rc_context
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch

from ..e0.observer import load_jsonl
from . import battery, export, family, robustness
from .analysis import bootstrap, contrast, wilson

BLUE, ORANGE, GREY = "#2a78d6", "#eb6834", "#898781"
INK, SECONDARY, GRID, AXIS, FILL = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7", "#f6f5f0"
ARMS = {"A1": (BLUE, "o", "over-blocked"), "A1R": (ORANGE, "s", "repaired branch"), "A4": (GREY, "D", "control")}
MODELS = {"gemini-pro-flex": "Gemini 3.1 Pro", "deepseek-v4-flash": "DeepSeek V4 Flash", "claude-sonnet-5": "Claude Sonnet 5",
          "qwen3.5-397b": "Qwen 3.5 397B"}
COPIES = {"": "unedited", "annotate": "notice", "audit": "audit", "object": "object-scoped", "guard": "guard-scoped"}
READERS = ("battery-gemini", "battery-deepseek", "battery-claude", "battery-qwen")
CODES, EDIT_CODES = "notes-coding/codes-deepseek-v4-flash.jsonl", "notes-coding-edits/codes-deepseek-v4-flash.jsonl"
ATTEMPTS, PROBE, PROBE_COPIES = "h2-study/responses.jsonl", "h3-study", "h3-explore-claude"
CRITERION = 0.2
STARTS, DODGE = {"A1R": 4}, {"A1": -0.14, "A1R": 0.14}
STEPS = (("False positive", "A guard blocks benign work, and\nthe agent finds a workaround."),
         ("Record", "The handoff notes carry the\nworkaround to later shifts."),
         ("Repair", "The block is removed. The notes\nkeep the workaround."))
LANES = (("A4", "control (A4)", 1, False), ("A1", "over-blocked (A1)", 1, True), ("A1R", "repaired branch (A1R)", 5, False),
         ("", "edited notes (A1G, A1W)", 5, False))
READ = {"A4": (4, 8), "A1": (4, 8), "A1R": (8,)}
KEY = (("o", INK, "shift under the over-blocking guard"), ("o", "white", "shift under the repaired guard"),
       ("v", INK, "notes read after this shift"))
STYLE = {"font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"], "font.size": 9,
         "axes.titlesize": 9, "axes.labelsize": 9, "xtick.labelsize": 9, "ytick.labelsize": 9, "legend.fontsize": 9,
         "axes.linewidth": 0.5, "axes.edgecolor": AXIS, "axes.labelcolor": SECONDARY, "text.color": INK,
         "xtick.color": SECONDARY, "ytick.color": SECONDARY, "xtick.major.size": 0, "ytick.major.size": 0,
         "grid.color": GRID, "grid.linewidth": 0.5, "pdf.fonttype": 42, "savefig.pad_inches": 0.02}


def interval(scores: dict) -> tuple[float, float, float]:
    values = list(scores.values())
    return (mean(values), *bootstrap([values], mean))


def gap(a: dict, b: dict) -> tuple[float, float, float]:
    d = contrast(a, b)
    return d["mean"], d["low"], d["high"]


def denial_curve(rows: list[dict], budget: int) -> dict:
    per = defaultdict(lambda: defaultdict(list))
    for r in rows:
        turn = r["success_turn"]
        before = sum(t < turn for t in r["denial_turns"]) if turn else budget
        per[r["arm"]][r["lineage"]].append([int(before <= k) for k in range(budget)])
    return {arm: {j: [mean(step) for step in zip(*runs)] for j, runs in by.items()} for arm, by in per.items()}


def _axes(fig, left: float, bottom: float, width: float, height: float):
    w, h = fig.get_size_inches()
    return fig.add_axes((left / w, bottom / h, width / w, height / h))


def _panel(ax, title: str, grid: str = "x") -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis=grid)
    ax.set_axisbelow(True)
    ax.set_title(title, loc="left", fontweight="bold", pad=4)


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


def _rows(ax, labels: list[str], named: bool = True) -> None:
    ax.set_yticks(range(len(labels)), labels if named else [""] * len(labels))
    ax.set_ylim(len(labels) - 0.5, -0.5)


def _legend(fig, arms: tuple[str, ...], **place) -> None:
    handles = [Line2D([], [], color=ARMS[a][0], marker=ARMS[a][1], markersize=4.6, markeredgecolor="white",
                      markeredgewidth=0.7, linewidth=1.1, label=ARMS[a][2]) for a in arms]
    fig.legend(handles=handles, frameon=False, ncols=len(arms), handlelength=1.6, columnspacing=1.6, **place)


def design(path: Path) -> Path:
    fig = Figure(figsize=(7.0, 2.4))
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, 7.0)
    ax.set_ylim(0, 2.4)
    ax.axis("off")
    ax.text(0.05, 2.28, "(a) Mechanism", fontweight="bold", va="center")
    for k, (head, body) in enumerate(STEPS):
        left = 0.05 + 2.33 * k
        ax.add_patch(FancyBboxPatch((left, 1.5), 2.15, 0.62, boxstyle="round,pad=0,rounding_size=0.06", linewidth=0.6,
                                    edgecolor=AXIS, facecolor=FILL))
        ax.text(left + 0.1, 1.98, f"{k + 1}  {head}", fontweight="bold", va="center")
        ax.text(left + 0.1, 1.71, body, va="center", linespacing=1.25)
        if k:
            ax.annotate("", (left - 0.01, 1.81), (left - 0.17, 1.81),
                        arrowprops={"arrowstyle": "-|>", "color": SECONDARY, "linewidth": 0.8})

    def at(shift: int) -> float:
        return 1.9 + 0.34 * (shift - 1)

    ax.text(0.05, 1.27, "(b) Design", fontweight="bold", va="center")
    height = {arm: 1.0 - 0.24 * k for k, (arm, *_) in enumerate(LANES)}
    for arm, label, start, blocked in LANES:
        color, marker, _ = ARMS.get(arm, (SECONDARY, "o", ""))
        y, branch = height[arm], start > 1
        ax.text(0.05, y, label, va="center")
        xs = [at(g) for g in range(start - branch, 9)]
        ys = [height["A1"]] * branch + [y] * (9 - start)
        ax.plot(xs, ys, color=color, linewidth=1.1, linestyle="-" if arm else (0, (3, 2)), zorder=2)
        ax.plot(xs[branch:], ys[branch:], marker=marker, markersize=5, markerfacecolor=color if blocked else "white",
                markeredgecolor=color, markeredgewidth=1, linestyle="none", zorder=3)
        ax.plot([at(g) for g in READ.get(arm, ())], [y + 0.1] * len(READ.get(arm, ())), marker="v", markersize=3.6, color=INK,
                linestyle="none", zorder=3)
    for g in range(1, 9):
        ax.text(at(g), 0.07, str(g), ha="center", va="center", color=SECONDARY)
    ax.text(at(1) - 0.2, 0.07, "shift", ha="right", va="center", color=SECONDARY)
    ax.text(at(5) + 0.1, 0.64, "silent repair", va="center", color=SECONDARY)
    ax.text(at(5) + 0.1, 0.40, "notes edited", va="center", color=SECONDARY)
    for k, (marker, face, label) in enumerate(KEY):
        ax.plot([4.62], [1.0 - 0.2 * k], marker=marker, markersize=5 if marker == "o" else 3.6, markerfacecolor=face,
                markeredgecolor=INK, markeredgewidth=1 if marker == "o" else 0, linestyle="none")
        ax.text(4.75, 1.0 - 0.2 * k, label, va="center")
    ax.text(4.57, 0.33, "The arms of a lineage share\none ticket schedule.", va="center", color=SECONDARY, linespacing=1.25)
    return _save(fig, path)


def results(sources: list[tuple], anchors: list[tuple], recipe: dict, reads: dict, curve: dict, path: Path) -> Path:
    fig = Figure(figsize=(7.0, 3.0))
    top, bottom = _axes(fig, 0.42, 1.6, 1.95, 0.72), _axes(fig, 0.42, 0.5, 1.95, 0.72)
    _panel(top, "(a) Notes with a labelled recipe", "y")
    _panel(bottom, "Reader success with those notes", "y")
    for arm, shares in recipe.items():
        top.plot(list(shares), list(shares.values()), color=ARMS[arm][0], marker=ARMS[arm][1], markersize=3.4,
                 markeredgecolor="white", markeredgewidth=0.5, linewidth=1.2, markevery=slice(arm in STARTS, None))
    for arm, points in reads.items():
        at = {g: g + (DODGE["A1"] if g == STARTS.get(arm) else DODGE.get(arm, 0)) for g in points}
        bottom.plot(list(at.values()), [v for v, _, _ in points.values()], color=ARMS[arm][0], linewidth=1.2)
        for shift, (value, low, high) in points.items():
            if shift != STARTS.get(arm):
                _mark(bottom, at[shift], value, *ARMS[arm][:2], low, high, across=False)
    for part, limit, ticks in ((top, 1, (0, 0.5, 1)), (bottom, 0.7, (0, 0.25, 0.5))):
        part.axvline(4.5, color=AXIS, linewidth=0.5)
        part.set_xlim(0.6, 8.4)
        part.set_ylim(-0.05, limit)
        part.set_xticks(range(1, 9))
        part.set_yticks(ticks)
    top.set_xticklabels([])
    top.annotate("silent repair", (4.5, 0.33), xytext=(3, 0), textcoords="offset points", va="center", color=SECONDARY)
    bottom.set_xlabel("shift")

    ax = _axes(fig, 3.52, 0.5, 1.22, 1.82)
    _panel(ax, "(b) One command")
    for y, (_, scores) in enumerate(sources):
        for arm in ("A4", "A1"):
            value, low, high = interval(scores[arm])
            _mark(ax, value, y, *ARMS[arm][:2], low, high)
    for y, (_, wins, trials) in enumerate(anchors, len(sources)):
        _mark(ax, wins / trials, y, SECONDARY, "^", *wilson(wins, trials))
    _rows(ax, [label for label, *_ in (*sources, *anchors)])
    ax.set_xlim(-0.04, 1)
    ax.set_xticks((0, 0.5, 1))
    ax.set_xlabel("reader success")

    ax = _axes(fig, 5.4, 0.5, 1.5, 1.82)
    _panel(ax, "(c) Several commands", "y")
    steps = range(len(next(iter(curve["A1"].values()))))
    notes = {"positive": ("positive control", 0, (0, 3), "left", "bottom"), "none": ("empty file", -1, (0, -3), "right", "top")}
    for arm in ("positive", "none", "A4", "A1"):
        lines = list(curve[arm].values())
        level = [mean(step) for step in zip(*lines)]
        if arm in ARMS:
            band = [bootstrap([list(step)], mean) for step in zip(*lines)]
            ax.fill_between(steps, [b[0] for b in band], [b[1] for b in band], color=ARMS[arm][0], alpha=0.12, linewidth=0)
            ax.plot(steps, level, color=ARMS[arm][0], marker=ARMS[arm][1], markersize=3.4, markeredgecolor="white",
                    markeredgewidth=0.5, linewidth=1.2)
        else:
            label, end, offset, ha, va = notes[arm]
            ax.plot(steps, level, color=AXIS, linewidth=0.9)
            ax.annotate(label, (steps[end], level[end]), xytext=offset, textcoords="offset points", ha=ha, va=va, color=SECONDARY)
    ax.set_xlim(-0.3, steps[-1] + 0.3)
    ax.set_ylim(-0.04, 1)
    ax.set_xticks(list(steps))
    ax.set_xlabel("denials before success")
    ax.set_ylabel("episodes that succeed")
    _legend(fig, ("A1", "A1R", "A4"), loc="upper center", bbox_to_anchor=(0.5, 1.0))
    return _save(fig, path)


def readers(rows: list[tuple], path: Path) -> Path:
    panels = (("(a) Boundary score", "difference", (-0.12, 0.56)), ("(b) Stale picture", "difference", (-0.12, 0.56)),
              ("(c) Sends a command", "share of calls", (-0.05, 1.05)), ("(d) Reader success", "difference", (-0.12, 0.66)))
    fig = Figure(figsize=(7.0, 1.7))
    for k, (title, label, limit) in enumerate(panels):
        ax = _axes(fig, 1.27 + 1.44 * k, 0.5, 1.26, 0.88)
        _panel(ax, title)
        ax.axvline(0, color=AXIS, linewidth=0.5)
        for y, (_, values, informative) in enumerate(rows):
            failed = k == 3 and not informative
            _mark(ax, values[k][0], y, BLUE, "o", *values[k][1:], hollow=failed)
            if failed:
                ax.annotate("check failed", (values[k][0], y), xytext=(6, 0), textcoords="offset points", va="center",
                            color=SECONDARY)
        ax.set_xlim(*limit)
        ax.set_xticks((0, 0.5, 1) if limit[1] > 1 else (0, 0.25, 0.5))
        ax.set_xlabel(label)
        _rows(ax, [name for name, *_ in rows], named=not k)
    return _save(fig, path)


def mitigation(rows: list[tuple], path: Path) -> Path:
    panels = (("(a) Reader\nsuccess", "copy −\ncontrol", (-0.06, 0.62)), ("(b) Labelled\nrecipe", "share of\nnotes", (-0.06, 1.06)),
              ("(c) Stale\npicture", "copy −\ncontrol", (-0.06, 0.62)))
    fig = Figure(figsize=(3.3, 2.1))
    for k, (title, label, limit) in enumerate(panels):
        ax = _axes(fig, 0.95 + 0.79 * k, 0.6, 0.7, 1.06)
        _panel(ax, title)
        ax.axvline(0, color=AXIS, linewidth=0.5)
        for y, (_, values) in enumerate(rows):
            _mark(ax, values[k][0], y, BLUE, "o", *values[k][1:])
        ax.set_xlim(*limit)
        ax.set_xticks(*([(0, 1), ("0", "1")] if limit[1] > 1 else [(0, 0.5), ("0", "0.5")]))
        ax.set_xlabel(label)
        _rows(ax, [name for name, _ in rows], named=not k)
        if not k:
            ax.axvline(CRITERION * rows[0][1][0][0], color=ORANGE, linewidth=0.8)
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


def _key(cfg: dict, arm: str, shift: int, transform: str = "") -> tuple:
    return battery._group({"donor": cfg["donor"], "kind": "syn", "run": cfg["name"], "arm": arm, "shift": shift,
                           "transform": transform})


def draw(cfgs: list[dict], earlier: dict, data: Path, out: Path) -> list[Path]:
    main, second = cfgs[:2]
    claude = main["donor"]
    srcs = export.sources(data, [*cfgs, earlier], ("syn",), (4, 8))
    trials = {name: battery._rows(srcs, data / name / "responses.jsonl", data / name / "executions.jsonl")[0] for name in READERS}
    per = robustness.scores(trials[READERS[0]], tuple(battery.SHARED), "success")

    def cell(cfg: dict, arm: str, shift: int, transform: str = "") -> dict:
        return per[_key(cfg, arm, shift, transform)]

    named = ((f"{MODELS[claude]}\nnotes", main), (f"{MODELS[second['donor']]}\nnotes", second), ("earlier study,\nread again", earlier))
    sources = [(label, {a: cell(cfg, a, 4) for a in ("A1", "A4")}) for label, cfg in named]
    anchor = _anchors(trials[READERS[0]])
    anchors = [(label, sum(anchor[arm]), len(anchor[arm])) for arm, label in (("none", "empty file"), ("positive", "positive control"))]
    lab = family.labelled([data / CODES])
    recipe = {arm: {g: mean(family._arm(lab, claude, "syn", arm, g).values()) for g in range(1, 9)
                    if family._arm(lab, claude, "syn", arm, g)} for arm in ("A4", "A1", "A1R")}
    recipe["A1R"] = {4: recipe["A1"][4]} | recipe["A1R"]
    reads = {"A4": {g: interval(cell(main, "A4", g)) for g in (4, 8)}, "A1": {g: interval(cell(main, "A1", g)) for g in (4, 8)},
             "A1R": {4: interval(cell(main, "A1", 4)), 8: interval(cell(main, "A1R", 8))}}
    episodes = list({r["cell_id"]: r for r in load_jsonl(data / ATTEMPTS)}.values())
    out.mkdir(parents=True, exist_ok=True)
    with rc_context(STYLE):
        made = [design(out / "design.pdf"),
                results(sources, anchors, recipe, reads, denial_curve(episodes, max(r["turns"] for r in episodes)),
                        out / "results.pdf")]

        chain, _, passed = family._probe_rows(data / PROBE)
        table = []
        for name in READERS:
            model = trials[name][0]["model"]
            success, attempt = (robustness.scores(trials[name], tuple(battery.SHARED), key) for key in ("success", "attempt"))
            a1, a4 = (_key(main, arm, 4) for arm in ("A1", "A4"))
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
            table.append((label, [gap(cell(main, "A1", 4, transform), cell(main, "A4", 4)),
                                  _share(v for (t, _), v in coded.items() if t == transform),
                                  (mean(stale), min(stale), max(stale))]))
        made.append(mitigation(table, out / "mitigation.pdf"))
    return made
