"""Predefined simulator smoke comparison; no model or production claims."""
import json
from pathlib import Path
from time import perf_counter
from benchmarks.diagnostic_env import make_tasks
from replayharbor.adapter import make_case
from replayharbor.core import Config, diagnose

OUT = Path(__file__).resolve().parents[1]/"experiments"/"simulation"
OUT.mkdir(parents=True, exist_ok=True)
protocol = dict(kind="scripted_simulation_smoke", budgets=[12,24,48],
                strategies=["uniform","coarse","adaptive"], trace_seed=1,
                tasks=[t.task_id for t in make_tasks()],
                reference="uniform, 100 replays per prefix; finite-sample descriptive reference",
                limitation="All simulator tasks are used for engineering smoke checks; no held-out efficacy claim.")
(OUT/"protocol.json").write_text(json.dumps(protocol,indent=2),encoding="utf-8")
rows=[]
for task in protocol["tasks"]:
    trace,replay=make_case(task,1)
    n=len(trace["snapshots"])
    reference=diagnose(n,replay,Config(n*100,"uniform",seed=9000000))
    for budget in protocol["budgets"]:
        for strategy in protocol["strategies"]:
            start=perf_counter()
            report=diagnose(n,replay,Config(budget,strategy))
            rows.append(dict(task=task,original_success=trace["final_success"],
                             budget=budget,strategy=strategy,seconds=perf_counter()-start,
                             reference_candidate=reference["candidate_prefix"],
                             candidate_matches_reference=report["candidate_prefix"]==reference["candidate_prefix"],
                             report=report))
(OUT/"runs.json").write_text(json.dumps(rows,indent=2),encoding="utf-8")
lines=["# Simulator smoke comparison", "",f"Tasks: {len(protocol['tasks'])}; runs: {len(rows)}.",
       "No model inference. Fixed strategies; finite-sample reference; engineering smoke scope.","",
       "| Budget | Strategy | Candidate agreement | Mean coverage |", "|---|---|---|---|"]
for budget in protocol["budgets"]:
    for strategy in protocol["strategies"]:
        cell=[r for r in rows if r['budget']==budget and r['strategy']==strategy]
        lines.append(f"| {budget} | {strategy} | {sum(r['candidate_matches_reference'] for r in cell)}/{len(cell)} | {sum(r['report']['coverage'] for r in cell)/len(cell):.1%} |")
lines.extend(["", "Agreement includes both methods returning no candidate. It does not establish diagnostic accuracy or root cause.",
              "Follow-up: held-out task templates, repeated references, independent confirmation, and real-model adapter validation."])
(OUT/"report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
print("\n".join(lines))
