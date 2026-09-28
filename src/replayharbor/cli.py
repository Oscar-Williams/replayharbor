"""A local, no-key workflow for inspecting and sharing synthetic failure evidence."""
import argparse
import hashlib
import html
import json
from pathlib import Path
from .core import Config
from .adapter import UPSTREAM_SHA
from .workflow import run_workflow
from .export_guard import assert_publishable


def write_bundle(target, task_id, trace_seed, report):
    assert_publishable({"task_id": task_id, "report": report})
    target = Path(target)
    target.mkdir(parents=True, exist_ok=False)
    case = dict(task_id=task_id, trace_seed=trace_seed, provenance="upstream_scripted_simulator",
                upstream_sha=UPSTREAM_SHA, config=report["config"])
    if "workflow_options" in report:
        case["workflow_options"] = report["workflow_options"]
    payloads = {"case.json": case, "report.json": report}
    hashes = {}
    for name, obj in payloads.items():
        raw = (json.dumps(obj, ensure_ascii=False, indent=2)+"\n").encode("utf-8")
        (target/name).write_bytes(raw)
        hashes[name] = hashlib.sha256(raw).hexdigest()
    (target/"manifest.json").write_text(json.dumps(hashes, indent=2), encoding="utf-8")
    (target/"issue.md").write_text(
        f"# ReplayHarbor diagnostic handoff\n\nTask: `{task_id}`\n\n"
        f"Evidence: scripted simulation, upstream `{UPSTREAM_SHA}`.\n\n"
        f"Candidate prefix: {report['candidate_prefix']}; coverage: {report['coverage']:.0%}.\n\n"
        f"Confirmation: {report.get('confirmation',{}).get('status','not_run')}.\n\n"
        f"Revision comparison: {report.get('revision',{}).get('status','not_run')}.\n\n"
        "Root cause remains unconfirmed. Review coverage and independent confirmation.\n\n"
        "Reproduce: `replayharbor verify PATH_TO_THIS_BUNDLE`\n", encoding="utf-8")
    escaped = html.escape(json.dumps(report, ensure_ascii=False, indent=2))
    confirmation = report.get("confirmation", {})
    revision = report.get("revision", {})
    workflow = ""
    if confirmation or revision:
        workflow = (
            '<h2>证据确认 / Confirmation</h2>'
            f'<p>Status: <strong>{html.escape(confirmation.get("status","not_run"))}</strong> · '
            f'Fresh replays: {confirmation.get("attempts",0)}</p>'
            f'<p>Failure increase interval: {html.escape(str(confirmation.get("failure_increase_interval","unavailable")))}</p>'
            '<h2>修订验证 / Revision comparison</h2>'
            f'<p>Status: <strong>{html.escape(revision.get("status","not_run"))}</strong> · '
            f'Completed pairs: {revision.get("completed_pairs",0)}</p>'
            f'<p>Failure rate: {revision.get("before_failure_rate","—")} → {revision.get("after_failure_rate","—")}</p>'
            f'<p>Reduction interval: {html.escape(str(revision.get("reduction_interval","unavailable")))}</p>'
            '<p>The intervention is supplied by the upstream scripted environment. '
            'Results describe this fixed case; other workflows need separate validation.</p>'
            f'<h2>下一步 / Next action</h2><p>{html.escape(report["next_action"])}</p>'
        )
    (target/"index.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>ReplayHarbor</title>'
        '<style>body{max-width:960px;margin:40px auto;padding:24px;font:17px system-ui;background:#f5f7fa;color:#172438}'
        'pre{white-space:pre-wrap;background:white;padding:24px;border-radius:12px}</style>'
        '<h1>ReplayHarbor · Diagnostic evidence</h1><p>Scripted simulation · No model inference</p>'
        f'<h2>Candidate: {report["candidate_prefix"]} · Coverage: {report["coverage"]:.0%}</h2>'
        '<p>A candidate identifies an association in replay evidence; root cause remains unconfirmed.</p>'
        + workflow + f'<details><summary>完整证据 / Full evidence</summary><pre>{escaped}</pre></details></html>', encoding="utf-8")


def verify_bundle(target):
    target = Path(target)
    hashes = json.loads((target/"manifest.json").read_text(encoding="utf-8"))
    if set(hashes) != {"case.json", "report.json"}:
        raise ValueError("unexpected manifest file set")
    for name, expected in hashes.items():
        if hashlib.sha256((target/name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"checksum mismatch: {name}")
    case = json.loads((target/"case.json").read_text(encoding="utf-8"))
    if case["upstream_sha"] != UPSTREAM_SHA:
        raise ValueError("unsupported upstream SHA")
    report = json.loads((target/"report.json").read_text(encoding="utf-8"))
    config = Config(**case["config"])
    if config.budget > 10000:
        raise ValueError("bundle exceeds offline verification replay limit")
    options = case.get("workflow_options", {})
    extra = sum(options.get(k,0) for k in ["confirmation_budget","comparison_budget"])
    if config.budget + extra > 10000:
        raise ValueError("bundle exceeds total offline verification replay limit")
    actual = run_workflow(case["task_id"], case["trace_seed"], config, options)
    if actual != report:
        raise ValueError("recomputed report differs from bundle")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    web = sub.add_parser('serve',help='start the loopback-only, no-key workbench')
    web.add_argument('--project-root',type=Path,default=Path.cwd())
    web.add_argument('--port',type=int,default=8765)
    run = sub.add_parser("demo")
    run.add_argument("--task", default="calendar_missing_timezone")
    run.add_argument("--trace-seed", type=int, default=1)
    run.add_argument("--budget", type=int, default=24)
    run.add_argument("--strategy", choices=["adaptive", "uniform", "coarse"], default="adaptive")
    run.add_argument("--out", type=Path, required=True)
    run.add_argument("--confirm-n", type=int, default=0, help="fixed fresh samples per prefix")
    run.add_argument("--confirm-budget", type=int, default=0)
    run.add_argument("--repair", help="explicit upstream synthetic intervention, e.g. clarify")
    run.add_argument("--compare-prefix", type=int, default=1)
    run.add_argument("--compare-n", type=int, default=128)
    run.add_argument("--compare-budget", type=int, default=0)
    check = sub.add_parser("verify")
    check.add_argument("bundle", type=Path)
    settings = sub.add_parser("check-config", help="validate local configuration without a network call")
    settings.add_argument("--project-root", type=Path, default=Path.cwd())
    probe = sub.add_parser("probe-model", help="official API authentication; optional bounded synthetic completion")
    probe.add_argument("--project-root", type=Path, default=Path.cwd())
    probe.add_argument("--completion", action="store_true")
    real = sub.add_parser("model-smoke", help="bounded real-inference smoke in a synthetic environment")
    real.add_argument("--project-root", type=Path, default=Path.cwd())
    real.add_argument("--out", type=Path, required=True)
    real.add_argument("--task-contract", choices=['original-v1','explicit-date-v2'], default='explicit-date-v2')
    args = parser.parse_args()
    try:
        if args.command == 'serve':
            from .workbench import serve
            serve(args.project_root,args.port)
        elif args.command == "check-config":
            from .settings import load_settings
            print(json.dumps(load_settings(args.project_root).public_summary()))
        elif args.command == "model-smoke":
            if args.out.exists():
                raise ValueError("output path exists; preserve previous runs")
            from .settings import load_settings
            from .model_replay import run_model_smoke
            settings = load_settings(args.project_root)
            settings.auth_headers()
            report = run_model_smoke(settings,args.task_contract)
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open('x',encoding='utf-8') as file:
                json.dump(report,file,ensure_ascii=False,indent=2)
            print(json.dumps(dict(status=report['status'],calls=report['ledger']['calls'],estimated_usd=report['ledger']['estimated_usd'])))
        elif args.command == "probe-model":
            from .settings import load_settings
            from .deepseek import probe, ProviderError
            try:
                print(json.dumps(probe(load_settings(args.project_root), args.completion)))
            except ProviderError as error:
                parser.exit(2, str(error)+"\n")
        elif args.command == "verify":
            verify_bundle(args.bundle)
            print("PASS: hashes and independently recomputed report match")
        else:
            if args.out.exists():
                raise ValueError("output directory already exists; choose a fresh run directory")
            options = {}
            if args.confirm_n:
                options.update(confirmation_n=args.confirm_n, confirmation_budget=args.confirm_budget)
            if args.repair:
                options.update(repair_type=args.repair, comparison_prefix=args.compare_prefix,
                               comparison_n=args.compare_n, comparison_budget=args.compare_budget)
            report = run_workflow(args.task, args.trace_seed, Config(args.budget, args.strategy), options)
            write_bundle(args.out, args.task, args.trace_seed, report)
            print(json.dumps({k: report[k] for k in ["attempts", "coverage", "candidate_prefix", "stop_reason"]}))
            if options:
                print(json.dumps(dict(total_attempts=report["total_attempts"],
                                      confirmation=report.get("confirmation",{}).get("status"),
                                      revision=report.get("revision",{}).get("status"))))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f"ReplayHarbor: {exc}\n")


if __name__ == "__main__":
    main()
