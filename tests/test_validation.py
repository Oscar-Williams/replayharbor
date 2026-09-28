import json
import hashlib
import pytest
from replayharbor.core import Config, diagnose
from replayharbor.validation import confirm_candidate, compare_revision, plan_seeds
from replayharbor.workflow import run_workflow
from replayharbor.cli import write_bundle, verify_bundle


def exploration():
    return diagnose(4, lambda k,s: k==1, Config(20,"uniform"))


def test_fresh_frozen_confirmation():
    initial=exploration()
    result=confirm_candidate(initial,lambda k,s:k==1,n=128,budget=256)
    assert result['status']=='supported'
    assert result['attempts']==256
    assert set(r['prefix'] for r in result['history'])=={0,1}
    assert set(r['seed'] for r in result['history']).isdisjoint(r['seed'] for r in initial['history'])
    assert not result['earliest_prefix_confirmed'] and not result['root_cause_confirmed']


def test_confirmation_contradiction_and_inconclusive():
    assert confirm_candidate(exploration(),lambda k,s:False,128,256)['status']=='not_supported'
    assert confirm_candidate(exploration(),lambda k,s:k==1,1,2)['status']=='inconclusive'


def test_confirmation_preflight_and_incomplete_samples():
    def fail(k,s):raise RuntimeError('private-api-key')
    r=confirm_candidate(exploration(),fail,128,255)
    assert r['status']=='insufficient_budget' and r['attempts']==0
    r=confirm_candidate(exploration(),fail,128,256)
    assert r['status']=='environment_error' and r['attempts']==1
    assert 'failure_increase_interval' not in r and 'private-api' not in json.dumps(r)
    no_candidate=diagnose(2,lambda k,s:False,Config(20))
    assert confirm_candidate(no_candidate,fail)['status']=='no_candidate'


@pytest.mark.parametrize('before,after,status',[(True,False,'improved'),(False,True,'regressed'),(True,True,'inconclusive')])
def test_paired_revision(before,after,status):
    a,b=[],[]
    def first(k,s):a.append(s);return before
    def second(k,s):b.append(s);return after
    r=compare_revision(first,second,1,n=128,budget=256)
    assert r['status']==status and a==b and len(set(a))==128
    assert r['completed_pairs']==128 and r['attempts']==256


def test_comparison_mid_pair_error():
    def fail(k,s):raise TimeoutError('private')
    r=compare_revision(lambda k,s:True,fail,1)
    assert r['attempts']==2 and r['completed_pairs']==0 and r['status']=='environment_error'
    assert 'reduction_interval' not in r


@pytest.mark.parametrize('n,budget,alpha',[(0,2,.05),(1,-1,.05),(1,2,0),(1,2,float('nan'))])
def test_invalid_plans(n,budget,alpha):
    with pytest.raises(ValueError):confirm_candidate(exploration(),lambda k,s:False,n,budget,alpha)


def test_seed_reproducibility():
    a=plan_seeds(20,100)
    assert a==plan_seeds(20,100)
    assert set(a).isdisjoint(plan_seeds(20,100,a))


def test_extended_bundle_recomputes(tmp_path):
    options=dict(confirmation_n=64,confirmation_budget=128,repair_type='clarify',
                 comparison_prefix=1,comparison_n=64,comparison_budget=128)
    report=run_workflow('calendar_missing_timezone',1,Config(),options)
    assert report['total_attempts']==280
    assert report['revision']['after_failure_rate']==0
    target=tmp_path/'case'
    write_bundle(target,'calendar_missing_timezone',1,report)
    assert verify_bundle(target)
    report['confirmation']['status']='invented'
    raw=json.dumps(report).encode()
    (target/'report.json').write_bytes(raw)
    manifest=json.loads((target/'manifest.json').read_text())
    manifest['report.json']=hashlib.sha256(raw).hexdigest()
    (target/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match='recomputed'):
        verify_bundle(target)
