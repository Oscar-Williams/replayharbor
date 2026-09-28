"""Fixed-sample evidence gates, separate from adaptive exploration.

Inference is conditional on independent replay outcomes from a fixed task/state.
Seed separation prevents reuse; it does not establish model independence.
"""
import math
import random


def plan_seeds(n, seed, excluded=()):
    if type(n) is not int or not 1 <= n <= 20000:
        raise ValueError("seed count must be an integer between 1 and 20000")
    rng = random.Random(seed)
    used = set(excluded)
    result = []
    while len(result) < n:
        value = rng.getrandbits(63)
        if value not in used:
            result.append(value)
            used.add(value)
    return result


def _validate(n, budget, alpha):
    if type(n) is not int or not 1 <= n <= 10000:
        raise ValueError("sample count must be an integer between 1 and 10000")
    if type(budget) is not int or budget < 0:
        raise ValueError("budget must be a nonnegative integer")
    if not 0 < alpha < 1:
        raise ValueError("alpha must lie strictly between zero and one")


def _outcome(replay, prefix, seed):
    value = replay(prefix, seed)
    if type(value) is not bool:
        raise TypeError("replay must return a boolean failure outcome")
    return value


def confirm_candidate(exploration, replay, n=512, budget=1024, alpha=0.05, seed=20260928, cancelled=lambda: False):
    """Confirm exactly one frozen candidate with fresh samples at 0 and k.

    Two simultaneous Hoeffding bounds via union bound; no earliest-prefix claim.
    Fixed sample size; an incomplete run has no inferential conclusion.
    """
    _validate(n, budget, alpha)
    candidate = exploration["candidate_prefix"]
    result = dict(status="not_requested", candidate_prefix=candidate, n_per_prefix=n,
                  alpha=alpha, seed=seed, budget=budget, planned_attempts=2*n,
                  attempts=0, history=[], root_cause_confirmed=False,
                  earliest_prefix_confirmed=False,
                  inference_scope="one frozen candidate and prefix 0; independent fixed-distribution replay assumption")
    if candidate is None:
        result.update(status="no_candidate", planned_attempts=0)
        return result
    if type(candidate) is not int or candidate <= 0 or candidate >= len(exploration["prefixes"]):
        raise ValueError("candidate must be a saved nonzero prefix")
    if budget < 2*n:
        result["status"] = "insufficient_budget"
        return result
    seeds = plan_seeds(2*n, seed, [row["seed"] for row in exploration["history"]])
    failures = {0: 0, candidate: 0}
    for i, value in enumerate(seeds):
        if cancelled():
            result['status']='cancelled'
            return result
        prefix = 0 if i < n else candidate
        row = dict(prefix=prefix, seed=value)
        result["history"].append(row)
        result["attempts"] += 1
        try:
            row["failed"] = _outcome(replay, prefix, value)
            failures[prefix] += row["failed"]
        except Exception as exc:
            row["error"] = type(exc).__name__
            result["status"] = "environment_error"
            return result
    radius = math.sqrt(math.log(4/alpha)/(2*n))
    bounds = {str(k): [max(0, f/n-radius), min(1, f/n+radius)] for k,f in failures.items()}
    p0, pk = bounds["0"], bounds[str(candidate)]
    diff = [pk[0]-p0[1], pk[1]-p0[0]]
    threshold, delta = exploration["config"]["p_fail"], exploration["config"]["delta"]
    if pk[0] >= threshold and diff[0] >= delta:
        status = "supported"
    elif pk[1] < threshold or diff[1] < delta:
        status = "not_supported"
    else:
        status = "inconclusive"
    result.update(status=status, failures={str(k):v for k,v in failures.items()},
                  failure_rate_intervals=bounds, failure_increase_interval=diff,
                  method="Hoeffding; union bound over two proportions")
    return result


def compare_revision(before, after, prefix, n=128, budget=256, alpha=0.05,
                     seed=20260929, excluded=(), cancelled=lambda: False):
    """Paired failure-rate reduction at a fixed prefix and user-selected revision."""
    _validate(n, budget, alpha)
    if type(prefix) is not int or prefix < 0:
        raise ValueError("prefix must be a nonnegative integer")
    result = dict(status="insufficient_budget", prefix=prefix, planned_pairs=n,
                  alpha=alpha, seed=seed, budget=budget, planned_attempts=2*n,
                  attempts=0, completed_pairs=0, history=[],
                  scope="paired replay of one fixed synthetic case; independent pairs assumed")
    if budget < 2*n:
        return result
    for value in plan_seeds(n, seed, excluded):
        if cancelled():
            result['status']='cancelled'
            return result
        row = dict(seed=value)
        result["history"].append(row)
        try:
            result["attempts"] += 1
            row["before_failed"] = _outcome(before, prefix, value)
            result["attempts"] += 1
            row["after_failed"] = _outcome(after, prefix, value)
        except Exception as exc:
            row["error"] = type(exc).__name__
            result["status"] = "environment_error"
            return result
        result["completed_pairs"] += 1
    rows = result["history"]
    fixed = sum(r["before_failed"] and not r["after_failed"] for r in rows)
    regressed = sum(not r["before_failed"] and r["after_failed"] for r in rows)
    effect = (fixed-regressed)/n
    # Pair difference lies in [-1, 1], range length 2.
    radius = math.sqrt(2*math.log(2/alpha)/n)
    bounds = [max(-1, effect-radius), min(1, effect+radius)]
    result.update(status="improved" if bounds[0] > 0 else "regressed" if bounds[1] < 0 else "inconclusive",
                  fixed_pairs=fixed, regressed_pairs=regressed, unchanged_pairs=n-fixed-regressed,
                  before_failure_rate=sum(r["before_failed"] for r in rows)/n,
                  after_failure_rate=sum(r["after_failed"] for r in rows)/n,
                  failure_rate_reduction=effect, reduction_interval=bounds,
                  method="paired Hoeffding bound on differences in [-1,1]")
    return result
