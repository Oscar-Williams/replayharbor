"""Maintainer workflow: explore, confirm, compare, then choose a next action."""
from .adapter import make_case
from .core import Config, diagnose
from .validation import confirm_candidate, compare_revision, _validate


def run_workflow(task_id, trace_seed, config, options=None, cancelled=lambda: False):
    options = options or {}
    allowed = {"confirmation_n", "confirmation_budget", "repair_type", "comparison_prefix",
               "comparison_n", "comparison_budget"}
    if set(options)-allowed:
        raise ValueError("unknown workflow options")
    config.validate()
    if "confirmation_n" in options:
        _validate(options["confirmation_n"], options.get("confirmation_budget",0),0.05)
    if options.get("repair_type"):
        _validate(options.get("comparison_n",128), options.get("comparison_budget",0),0.05)
    # Check a user-selected intervention before any potentially costly calls.
    revised = None
    if options.get("repair_type"):
        _, revised = make_case(task_id, trace_seed, options["repair_type"])
    trace, replay = make_case(task_id, trace_seed)
    if revised is not None and not 0 <= options.get("comparison_prefix",1) < len(trace["snapshots"]):
        raise ValueError("comparison prefix outside saved snapshots")
    report = diagnose(len(trace["snapshots"]), replay, config, cancelled)
    if not options:
        return report  # v1 bundle compatibility
    report["workflow_options"] = options
    if options.get("confirmation_n"):
        report["confirmation"] = confirm_candidate(
            report, replay, n=options["confirmation_n"], budget=options.get("confirmation_budget",0), cancelled=cancelled)
    if revised is not None:
        used = [r["seed"] for r in report["history"]]
        used += [r["seed"] for r in report.get("confirmation",{}).get("history",[])]
        report["revision"] = compare_revision(
            replay, revised, options.get("comparison_prefix",1),
            n=options.get("comparison_n",128), budget=options.get("comparison_budget",0), excluded=used, cancelled=cancelled)
        report["revision"]["intervention"] = options["repair_type"]
        report["revision"]["provenance"] = "user-selected upstream scripted intervention; not a generated patch"
    report["total_attempts"] = report["attempts"] + report.get("confirmation",{}).get("attempts",0) + report.get("revision",{}).get("attempts",0)
    confirmation = report.get("confirmation",{}).get("status")
    report["next_action"] = (
        "Review candidate evidence and test a user-selected revision; root cause and earliest position remain unconfirmed."
        if confirmation == "supported" else
        "Review the frozen evidence and design a new independent run; retain this inconclusive or unsupported result.")
    return report
