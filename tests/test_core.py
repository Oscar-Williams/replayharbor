from copy import deepcopy
import json
import pytest
from replayharbor.core import Config, diagnose
from replayharbor.adapter import make_case
from replayharbor.cli import write_bundle, verify_bundle


@pytest.mark.parametrize("budget", [0, 1, 2, 7, 24])
@pytest.mark.parametrize("strategy", ["adaptive", "uniform", "coarse"])
def test_hard_budget(budget, strategy):
    calls=[]
    report=diagnose(9, lambda k,s: calls.append((k,s)) is None, Config(budget, strategy))
    assert len(calls)==report["attempts"]==budget
    assert sum(r["n"] for r in report["prefixes"])==budget
    assert report["root_cause_confirmed"] is False


def test_nonmonotonic_curve_and_missing_coverage():
    result=diagnose(5, lambda k,s:k in {1,3},Config(50,"uniform"))
    assert result["candidate_prefix"]==1
    partial=diagnose(5,lambda k,s:False,Config(2))
    assert partial["untested_prefixes"]==[1,2,3,4]
    assert partial["conclusion"]=="insufficient_evidence"


def test_failures_and_cancellation_consume_no_extra_calls():
    def fail(k,s):raise RuntimeError("sensitive private content")
    report=diagnose(3,fail,Config(24))
    assert report["attempts"]==1 and report["successful_replays"]==0
    assert "sensitive" not in json.dumps(report)
    assert diagnose(3,fail,Config(),lambda:True)["attempts"]==0


def test_snapshot_isolation_and_bundle_roundtrip(tmp_path):
    trace,replay=make_case()
    before=deepcopy(trace)
    first=replay(1,101)
    assert replay(1,101)==first and trace==before
    report=diagnose(len(trace["snapshots"]),replay,Config())
    folder=tmp_path/"bundle"
    write_bundle(folder,"calendar_missing_timezone",1,report)
    assert verify_bundle(folder)
    (folder/"case.json").write_text("{}")
    with pytest.raises(ValueError,match="checksum"):
        verify_bundle(folder)


def test_invalid_inputs():
    with pytest.raises(ValueError):diagnose(0,lambda k,s:False,Config())
    with pytest.raises(ValueError):diagnose(1,lambda k,s:False,Config(-1))
