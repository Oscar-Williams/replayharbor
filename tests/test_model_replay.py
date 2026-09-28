from copy import deepcopy
import json
import pytest
from replayharbor.settings import Settings
from replayharbor.model_replay import (BoundedModel,BudgetExceeded,build_model_prompt,
                                      run_episode,exact_step,parse_action)


def task():
    from benchmarks.diagnostic_env import make_tasks
    return next(t for t in make_tasks() if t.task_id=='calendar_missing_timezone')


def test_no_hidden_labels_in_prompt():
    value=task()
    value.metadata['private_marker']='hidden_ground_truth'
    value.required_effects=['secret_effect_label']
    prompt=build_model_prompt(value,[])
    assert 'hidden_ground_truth' not in prompt and 'secret_effect_label' not in prompt
    assert 'America/Los_Angeles' not in prompt
    updated=build_model_prompt(value,[],'explicit-date-v2')
    assert '2026-05-09' in updated
    assert 'hidden_ground_truth' not in updated and 'secret_effect_label' not in updated
    assert 'America/Los_Angeles' not in updated


def test_exact_arguments_prevent_partial_false_success():
    value=task()
    action=parse_action(json.dumps(dict(kind='tool',tool_name='create_event',tool_args={
        'attendee':'Lee','date':'2026-05-09','time':'10:00','timezone':'Europe/London'})),value)
    assert exact_step(value,action) is None
    with pytest.raises(ValueError):parse_action('{"kind":"tool","tool_name":"shell"}',value)


def test_snapshot_restoration_with_independent_model_calls():
    value=task()
    actions=[dict(kind='clarify',tool_args={'field':'timezone'}),
             dict(kind='tool',tool_name='search_availability',tool_args={'attendee':'Lee','date':'2026-05-09','time':'10:00','timezone':'America/Los_Angeles'}),
             dict(kind='tool',tool_name='create_event',tool_args={'attendee':'Lee','date':'2026-05-09','time':'10:00','timezone':'America/Los_Angeles'}),
             dict(kind='final',final_answer='Done')]
    class Model:
        def __init__(self,items):self.items=iter(items)
        def complete(self,prompt):return json.dumps(next(self.items))
    baseline=run_episode(value,Model(actions))
    assert baseline['final_success']
    snapshot=deepcopy(baseline['snapshots'][1])
    resumed=run_episode(value,Model(actions[1:]),snapshot)
    assert resumed['final_success'] and snapshot==baseline['snapshots'][1]


def test_budget_blocks_network_and_failed_call_keeps_reservation(monkeypatch):
    from replayharbor.deepseek import ProviderError
    requests=[]
    def request(*args):requests.append(1);raise ProviderError('test transport failure')
    monkeypatch.setattr('replayharbor.model_replay._request',request)
    settings=Settings('sk-'+'z'*32,'https://api.deepseek.com','deepseek-flash')
    model=BoundedModel(settings,cap_usd=.0000001)
    with pytest.raises(BudgetExceeded):model.complete('synthetic')
    assert requests==[]
    model=BoundedModel(settings,max_calls=1)
    with pytest.raises(ProviderError):model.complete('synthetic')
    assert len(model.entries)==1 and model.charged_estimate>0
    with pytest.raises(BudgetExceeded):model.complete('synthetic')
    assert len(requests)==1
