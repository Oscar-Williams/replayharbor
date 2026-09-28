"""Frozen scheduler transfer check on reserved medium/hard template groups."""
from collections import defaultdict
import json
from pathlib import Path
from replayharbor.adapter import verify_upstream, UPSTREAM_SHA
from replayharbor.core import Config, diagnose


def main():
    verify_upstream()
    from benchmarks.local_task_suite import make_local_tasks
    from replay.trace_logger import run_episode
    from replay.prefix_replay import replay_from_prefix
    root=Path(__file__).resolve().parents[1]
    out=root/'experiments/heldout'
    out.mkdir(exist_ok=False)
    tasks=make_local_tasks()
    groups=defaultdict(list)
    for task in tasks:groups[(task.family,task.metadata['difficulty'])].append(task)
    selected=[t for key,group in sorted(groups.items()) if key[1] in {'medium','hard'} for t in sorted(group,key=lambda t:t.task_id)[:2]]
    protocol=dict(upstream_sha=UPSTREAM_SHA,selected=[t.task_id for t in selected],
                  split='all easy groups reserved for development; first two IDs per medium/hard family group for evaluation',
                  trace_seed=1,budgets=[12,24,48],strategies=['uniform','coarse','adaptive'],
                  reference_n_per_prefix=128,reference_seeds=[8100000,9100000],
                  limitation='prospective transfer check after initial 25-task study; shared scripted mechanisms and correlated templates; reference is finite and is not ground truth; no tuning from these results')
    # Added after the first audit: a task-suite capability gate prevents an all-normal
    # reference from being interpreted as diagnostic accuracy.
    protocol['task_capability_audit']=[dict(task=t.task_id,error_rate=t.error_rate,faulty_steps=len(t.faulty_steps)) for t in selected]
    protocol['efficacy_eligible']=all(t.error_rate>0 and t.faulty_steps for t in selected)
    (out/'protocol.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    results=[]
    for task in selected:
        trace=run_episode(task,seed=1,mode='imperfect')
        def replay(k,seed):
            return not replay_from_prefix(task,trace,k,[seed],mode='imperfect')['runs'][0]['final_success']
        size=len(trace['snapshots'])
        refs=[diagnose(size,replay,Config(128*size,'uniform',seed=seed)) for seed in protocol['reference_seeds']]
        runs=[diagnose(size,replay,Config(budget,strategy)) for budget in protocol['budgets'] for strategy in protocol['strategies']]
        results.append(dict(task=task.task_id,baseline_success=trace['final_success'],references=refs,runs=runs))
    stable=[r for r in results if r['references'][0]['candidate_prefix']==r['references'][1]['candidate_prefix']]
    summary=dict(tasks=len(results),reference_candidate_stable=len(stable),
                 reference_candidate_unstable=len(results)-len(stable),stable_reference_candidate_present=sum(r['references'][0]['candidate_prefix'] is not None for r in stable),comparisons=[])
    for budget in protocol['budgets']:
        for strategy in protocol['strategies']:
            subset=[next(x for x in r['runs'] if x['config']['budget']==budget and x['config']['strategy']==strategy) for r in stable]
            summary['comparisons'].append(dict(budget=budget,strategy=strategy,denominator=len(stable),
                agreement_including_both_none=sum(x['candidate_prefix']==r['references'][0]['candidate_prefix'] for r,x in zip(stable,subset)),
                candidate_present_agreement=sum(x['candidate_prefix']==r['references'][0]['candidate_prefix'] for r,x in zip(stable,subset) if r['references'][0]['candidate_prefix'] is not None),
                mean_coverage=sum(x['coverage'] for x in subset)/len(subset) if subset else None))
    (out/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary))


if __name__=='__main__':main()
