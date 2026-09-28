"""Bridge to the independently installed, pinned Delta-MFP package."""
from importlib.metadata import version, distribution
from functools import lru_cache
import json
from pathlib import Path
import subprocess
from urllib.parse import urlparse
from urllib.request import url2pathname

UPSTREAM_SHA = "c01fbafca01d34e5e7492d48f856d75bf6f7b8ec"


@lru_cache(maxsize=1)
def verify_upstream():
    if version("delta-mfp-local-agents") != "1.1.0":
        raise ValueError("Delta-MFP 1.1.0 is required; see upstream.lock.json")
    source = json.loads(distribution("delta-mfp-local-agents").read_text("direct_url.json") or "{}")
    if source.get("vcs_info", {}).get("commit_id") == UPSTREAM_SHA:
        return
    if source.get("dir_info", {}).get("editable") and source.get("url", "").startswith("file:"):
        path = Path(url2pathname(urlparse(source["url"]).path))
        head = subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()
        dirty = subprocess.check_output(["git", "-C", str(path), "status", "--porcelain", "--untracked-files=no"], text=True).strip()
        if head == UPSTREAM_SHA and not dirty:
            return
    raise ValueError("upstream provenance mismatch: install the pinned clean revision")


def make_case(task_id="calendar_missing_timezone", trace_seed=1, repair_type=None):
    verify_upstream()
    from benchmarks.diagnostic_env import make_tasks
    from replay.trace_logger import run_episode
    from replay.prefix_replay import replay_from_prefix
    task = next((t for t in make_tasks() if t.task_id == task_id), None)
    if task is None:
        raise ValueError("unknown built-in task id")
    if repair_type is not None and repair_type not in task.repair_map:
        raise ValueError("unsupported intervention for this task; inspect task repair_map")
    trace = run_episode(task, seed=trace_seed, mode="imperfect")

    def replay(k, seed):
        result = replay_from_prefix(task, trace, k, [seed], mode="imperfect", repair_type=repair_type)
        return not result["runs"][0]["final_success"]

    return trace, replay
