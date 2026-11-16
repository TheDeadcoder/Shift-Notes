import argparse
import json
from pathlib import Path

import yaml
from dotenv import load_dotenv

from ..sandbox.container import Container
from . import (analysis, battery, behavior, calibration, chains, coding, export, family, mitigations, notes_coding, potency,
               probe, robustness, vignettes)


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="python -m swarmgate.e1")
    parser.add_argument("--observers-file", default="configs/observers.yaml")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("probe")
    p.add_argument("--models", required=True)
    p.add_argument("--samples", type=int, default=3)
    p.add_argument("--roles", default="donor,attacker")
    p.add_argument("--out", default="runs/probe/responses.jsonl")
    s = sub.add_parser("probe-summary")
    s.add_argument("--out", default="runs/probe/responses.jsonl")
    v = sub.add_parser("vignettes")
    v.add_argument("--models", required=True)
    v.add_argument("--samples", type=int, default=30)
    v.add_argument("--out", default="runs/vignettes/responses.jsonl")
    c = sub.add_parser("code")
    c.add_argument("--coder", required=True)
    c.add_argument("--source", default="runs/vignettes/responses.jsonl")
    c.add_argument("--out", required=True)
    c.add_argument("--share", type=float, default=1.0)
    r = sub.add_parser("vignette-report")
    r.add_argument("--run", default="runs/vignettes")
    for name in ("calibrate", "pilot", "chains", "score", "potency-report"):
        sub.add_parser(name).add_argument("--config", required=True)
    sub.choices["chains"].add_argument("--status", action="store_true")
    sub.choices["score"].add_argument("--generations", default="2,4")
    sub.choices["score"].add_argument("--workers", type=int, default=6)
    for name in ("battery", "battery-report"):
        b = sub.add_parser(name)
        b.add_argument("--configs", default="configs/e1.yaml,configs/e1-ow.yaml")
        b.add_argument("--out", default="runs/battery")
        b.add_argument("--anchors-only", action="store_true")
        b.add_argument("--kinds")
        b.add_argument("--shifts")
        b.add_argument("--edits")
        b.add_argument("--transforms", default=",".join(t for t in mitigations.TRANSFORMS if t != "wipe"))
    sub.choices["battery"].add_argument("--objectives", choices=("all", "shared"), default="all")
    sub.choices["battery"].add_argument("--anchor-samples", type=int, default=battery.SAMPLES)
    sub.choices["battery"].add_argument("--reader", default="claude-sonnet-5")
    sub.choices["battery"].add_argument("--rpm", type=int)
    sub.choices["battery"].add_argument("--workers", type=int)
    sub.choices["battery"].add_argument("--exec-workers", type=int, default=8)
    sub.choices["battery"].add_argument("--api-key-env")
    sub.choices["battery"].add_argument("--lenient", action="store_true")
    sub.choices["battery-report"].add_argument("--public")
    sub.add_parser("chain-report").add_argument("--configs", default="configs/e1.yaml,configs/e1-ow.yaml")
    f = sub.add_parser("v2-report")
    f.add_argument("--configs", default="configs/e1-v2.yaml,configs/e1-v2-ow.yaml")
    f.add_argument("--battery", default="runs/v2/battery-gemini")
    f.add_argument("--shifts", default="4,8")
    f.add_argument("--edits")
    f.add_argument("--coding", default="runs/v2/notes-coding/codes-deepseek-v4-flash.jsonl")
    f.add_argument("--multi-turn")
    f.add_argument("--probe")
    f.add_argument("--readers")
    f.add_argument("--explore")
    f.add_argument("--public")
    x = sub.add_parser("export-tables")
    x.add_argument("--configs", default="configs/e1.yaml,configs/e1-ow.yaml")
    x.add_argument("--battery", default="runs/battery,runs/battery-gemini")
    x.add_argument("--coding", default="runs/notes-coding")
    x.add_argument("--out", default="results/e1")
    x = sub.add_parser("export-records")
    x.add_argument("--configs", default=",".join(f"configs/{name}.yaml" for name in (
        "e1-v2", "e1-v2-ow", "e1-v2-effect", "e1-v2-effect-ow", "e1-v2-nogf", "e1-v2-hygiene", "e1-v2-mitigation", "e1")))
    x.add_argument("--battery", default=",".join(f"runs/v2/battery-{name}" for name in ("gemini", "deepseek", "claude", "qwen")))
    x.add_argument("--coding", default=",".join(f"runs/v2/notes-coding{name}" for name in (
        "", "-edits", "-nogf", "-hygiene", "-mitigation")))
    x.add_argument("--attempts", default="runs/v2/h2-study")
    x.add_argument("--probe", default=",".join(f"runs/v2/h3-{name}" for name in (
        "study", "explore-claude", "explore-qwen", "explore-effect", "explore-effect-ow")))
    x.add_argument("--edits", default="runs/v2/mitigations/edits.jsonl")
    x.add_argument("--out", default="results/v2")
    h = sub.add_parser("hand-bundle")
    h.add_argument("--configs", default="configs/e1.yaml,configs/e1-ow.yaml")
    h.add_argument("--out", default="runs/hand-coding")
    h.add_argument("--n", type=int, default=60)
    h.add_argument("--seed", type=int, default=0)
    h = sub.add_parser("hand-report")
    h.add_argument("--dir", default="runs/hand-coding")
    h.add_argument("--coders", default="runs/notes-coding/codes-deepseek-v4-flash.jsonl,runs/notes-coding/codes-gemini.jsonl")
    for name in ("notes-code", "notes-code-report"):
        n = sub.add_parser(name)
        n.add_argument("--configs", default="configs/e1.yaml,configs/e1-ow.yaml")
        n.add_argument("--out", default="runs/notes-coding")
        n.add_argument("--rubric", choices=tuple(notes_coding.RUBRICS), default="notes")
    sub.choices["notes-code"].add_argument("--coder", required=True)
    sub.choices["notes-code"].add_argument("--share", type=float, default=1.0)
    sub.choices["notes-code"].add_argument("--donor")
    sub.choices["notes-code"].add_argument("--file")
    sub.choices["notes-code"].add_argument("--rpm", type=int)
    sub.choices["notes-code"].add_argument("--workers", type=int)
    sub.choices["notes-code"].add_argument("--api-key-env")
    sub.choices["notes-code"].add_argument("--edits")
    sub.choices["notes-code"].add_argument("--shifts")
    for name in ("mitigate", "mitigate-report"):
        m = sub.add_parser(name)
        m.add_argument("--out", default="runs/mitigations")
    m = sub.choices["mitigate"]
    m.add_argument("--configs", default="configs/e1.yaml")
    m.add_argument("--editor", default="claude-sonnet-5")
    m.add_argument("--arm", default="A1")
    m.add_argument("--shift", type=int, default=4)
    m.add_argument("--kind", default="syn")
    m.add_argument("--lineages")
    m.add_argument("--transforms", default=",".join(mitigations.TRANSFORMS))
    m.add_argument("--api-key-env")
    sub.choices["mitigate-report"].add_argument("--codes")
    sub.choices["mitigate-report"].add_argument("--original")
    for name in ("notes-code", "notes-code-report"):
        sub.choices[name].add_argument("--primary")
        sub.choices[name].add_argument("--second")
    args = parser.parse_args()
    if args.cmd == "vignette-report":
        print("\n".join(analysis.vignette_report(Path(args.run))))
        return
    if args.cmd == "hand-report":
        print("\n".join(notes_coding.human_report(Path(args.dir), [Path(p) for p in args.coders.split(",")])))
        return
    if args.cmd == "mitigate-report":
        paths = [Path(p) if p else None for p in (args.codes, args.original)]
        print("\n".join(mitigations.report(Path(args.out) / mitigations.FILE, *paths)))
        return
    if args.cmd == "v2-report":
        cfgs = [yaml.safe_load(Path(p).read_text()) for p in args.configs.split(",")]
        shifts = tuple(int(g) for g in args.shifts.split(","))
        if args.public:
            srcs = export.sources(Path(args.public), cfgs, ("syn",), shifts)
        else:
            edits = mitigations.edited(Path(args.edits)) if args.edits else None
            srcs = battery.sources(cfgs, kinds=("syn",), shifts=shifts, edits=edits)
        out = Path(args.battery)
        per, controls = battery.lineage_scores(srcs, out / "responses.jsonl", out / "executions.jsonl")
        donors = list(dict.fromkeys(c["donor"] for c in cfgs))
        print("\n".join(family.report(per, controls, donors, [Path(p) for p in args.coding.split(",")],
                                      {s["arm"] for s in srcs.values() if s.get("control")}, shifts,
                                      Path(args.multi_turn) if args.multi_turn else None,
                                      Path(args.probe) if args.probe else None)))
        if args.readers:
            print("\n".join(robustness.readers(srcs, [Path(p) for p in args.readers.split(",")], donors, shifts)))
        for folder in args.explore.split(",") if args.explore else ():
            print("\n".join([f"probe folder {folder}"] + family.probe_groups(Path(folder))))
        return
    if args.cmd in ("export-tables", "export-records", "hand-bundle"):
        cfgs = [yaml.safe_load(Path(p).read_text()) for p in args.configs.split(",")]
        if args.cmd == "hand-bundle":
            print(json.dumps(notes_coding.bundle(cfgs, Path(args.out), args.n, args.seed)))
        elif args.cmd == "export-records":
            folders = {kind: [Path(p) for p in getattr(args, kind).split(",") if p] for kind in export.KEPT}
            print(json.dumps(export.public(cfgs, Path(args.out), folders, Path(args.edits) if args.edits else None)))
        else:
            folders = [Path(p) for p in args.battery.split(",")]
            print(json.dumps(export.tables(cfgs, Path(args.out), folders, Path(args.coding))))
        return
    specs = yaml.safe_load(Path(args.observers_file).read_text())
    cfg = yaml.safe_load(Path(args.config).read_text()) if "config" in args else {}
    out_dir = Path(cfg.get("out", "runs/e1"))

    if args.cmd == "calibrate":
        box = Container(f"sg-calibrate-{cfg['name']}")
        try:
            print("\n".join(calibration.calibrate(cfg, box)))
        finally:
            box.close()
        return
    if args.cmd == "pilot":
        print(json.dumps(chains.pilot(cfg, specs, out_dir)))
        print("\n".join(chains.pilot_report(cfg, out_dir, specs)))
        return
    if args.cmd == "chains":
        if not args.status:
            print(json.dumps(chains.run(cfg, specs, out_dir)))
        print("\n".join(chains.progress(cfg, out_dir, chains.model_prices(specs, cfg["donor"]))))
        return
    if args.cmd == "score":
        generations = tuple(int(g) for g in args.generations.split(","))
        print(json.dumps(potency.score_run(cfg, out_dir, generations, args.workers)))
        return
    if args.cmd == "potency-report":
        print("\n".join(analysis.potency_report(out_dir, cfg["generations"])))
        return
    if args.cmd in ("battery", "battery-report"):
        cfgs = [yaml.safe_load(Path(p).read_text()) for p in args.configs.split(",")]
        shifts = tuple(int(g) for g in args.shifts.split(",")) if args.shifts else None
        kinds, transforms = tuple(args.kinds.split(",")) if args.kinds else None, tuple(args.transforms.split(","))
        if getattr(args, "public", None):
            srcs = export.sources(Path(args.public), cfgs, kinds, shifts, transforms)
        else:
            edits = mitigations.edited(Path(args.edits), transforms) if args.edits else None
            srcs = battery.sources(cfgs, args.anchors_only, kinds, shifts, edits)
        out = Path(args.out)
        responses, executions = out / "responses.jsonl", out / "executions.jsonl"
        if args.cmd == "battery":
            spec = dict(specs[args.reader])
            spec.update({k: v for k, v in (("rpm", args.rpm), ("workers", args.workers),
                                           ("api_key_env", args.api_key_env)) if v})
            objectives = tuple(battery.SHARED if args.objectives == "shared" else battery.GOALS)
            print(json.dumps(battery.run({args.reader: spec}, srcs, responses, objectives, args.anchor_samples)))
            print(json.dumps(battery.execute(srcs, responses, executions, args.exec_workers)))
            if args.lenient:
                print(json.dumps(battery.execute(srcs, responses, out / battery.LENIENT, args.exec_workers, ("prose",))))
        print("\n".join(battery.report(srcs, responses, executions)))
        return
    if args.cmd == "chain-report":
        cfgs = [yaml.safe_load(Path(p).read_text()) for p in args.configs.split(",")]
        print("\n".join(behavior.chain_report(cfgs)))
        return
    if args.cmd in ("notes-code", "notes-code-report"):
        cfgs = [yaml.safe_load(Path(p).read_text()) for p in args.configs.split(",")]
        out = Path(args.out)
        prefix = "codes" if args.rubric == "notes" else args.rubric
        if args.cmd == "notes-code":
            spec = dict(specs[args.coder])
            spec.update({k: v for k, v in (("rpm", args.rpm), ("workers", args.workers),
                                           ("api_key_env", args.api_key_env)) if v})
            target = out / (args.file or f"{prefix}-{args.coder}.jsonl")
            pool = mitigations.edited(Path(args.edits)) if args.edits else None
            shifts = tuple(int(g) for g in args.shifts.split(",")) if args.shifts else None
            print(json.dumps(notes_coding.run({args.coder: spec}, cfgs, target, args.share, donor=args.donor, pool=pool,
                                              rubric=args.rubric, shifts=shifts)))
            if pool is not None:
                return
        report = notes_coding.report if args.rubric == "notes" else notes_coding.repair_report
        print("\n".join(report(out / (args.primary or f"{prefix}-deepseek-v4-flash.jsonl"),
                               out / (args.second or f"{prefix}-second.jsonl"))))
        return
    if args.cmd == "mitigate":
        cfgs = [yaml.safe_load(Path(p).read_text()) for p in args.configs.split(",")]
        spec = dict(specs[args.editor]) | ({"api_key_env": args.api_key_env} if args.api_key_env else {})
        lineages = {int(j) for j in args.lineages.split(",")} if args.lineages else None
        chosen = mitigations.select(cfgs, args.arm, args.shift, args.kind, lineages=lineages)
        target = Path(args.out) / mitigations.FILE
        print(json.dumps(mitigations.run({args.editor: spec}, chosen, target, tuple(args.transforms.split(",")))))
        print("\n".join(mitigations.report(target)))
        return

    if args.cmd in ("probe", "probe-summary"):
        if args.cmd == "probe":
            chosen = {name: specs[name] for name in args.models.split(",")}
            print(json.dumps(probe.run(chosen, Path(args.out), args.samples, roles=tuple(args.roles.split(",")))))
        print("\n".join(probe.summary(Path(args.out))))
    elif args.cmd == "vignettes":
        chosen = {name: specs[name] for name in args.models.split(",")}
        print(json.dumps(vignettes.run(chosen, Path(args.out), args.samples)))
    else:
        coder = {args.coder: specs[args.coder]}
        print(json.dumps(coding.run(coder, args.coder, Path(args.source), Path(args.out), args.share)))


if __name__ == "__main__":
    main()
