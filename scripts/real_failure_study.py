"""Predeclared engineering control: observed-tool corruption and rollback."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from replayharbor.adapter import verify_upstream
from replayharbor.settings import load_settings
from replayharbor.model_replay import BoundedModel, run_episode, BudgetExceeded
from replayharbor.deepseek import ProviderError
from replayharbor.export_guard import assert_publishable


def main():
    root=Path(__file__).resolve().parents[1]
    out=root/'experiments/deepseek/controlled-failure'
    out.mkdir(exist_ok=False)
    source=root/'experiments/deepseek/run-002.json'
    previous=json.loads(source.read_text(encoding='utf-8'))
    verify_upstream()
    from benchmarks.diagnostic_env import make_tasks
    task=next(t for t in make_tasks() if t.task_id=='calendar_missing_timezone')
    normal=previous['baseline']['snapshots'][1]
    assert normal['history'][-1]['tool_result']['answer']=='America/Los_Angeles'
    faulty=deepcopy(normal)
    faulty['history'][-1]['tool_result']['answer']='UTC'
    snapshots={'normal':normal,'corrupted_observation':faulty,
               'rollback':previous['baseline']['snapshots'][0]}
    order=['normal','corrupted_observation','rollback','rollback','corrupted_observation','normal']
    protocol=dict(date='2026-09-28',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  task=task.task_id,contract='explicit-date-v2',order=order,max_steps=4,
                  max_calls=24,cap_usd=.10,intervention='replace observed clarification answer with UTC; rollback restores pre-clarification snapshot',
                  scope='two repeats per engineering control; synthetic environment; no causal generalization or accuracy estimate')
    (out/'protocol.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    model=BoundedModel(load_settings(root))
    result=dict(protocol=protocol,runs=[],status='running')
    try:
        for condition in order:
            run=run_episode(task,model,snapshots[condition],max_steps=4,task_contract='explicit-date-v2')
            result['runs'].append(dict(condition=condition,run=run))
        result['status']='completed'
    except (BudgetExceeded,ProviderError,ValueError,KeyError,TypeError) as exc:
        result.update(status='stopped',error_type=type(exc).__name__)
    finally:
        result['ledger']=model.public_ledger()
        assert_publishable(result)
        (out/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(status=result['status'],outcomes=[dict(condition=r['condition'],success=r['run']['final_success']) for r in result['runs']],calls=result['ledger']['calls'],estimated_usd=result['ledger']['estimated_usd'])))


if __name__=='__main__':main()
