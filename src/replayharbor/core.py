"""Scheduling sees only observed Bernoulli outcomes, never task truth labels."""
from dataclasses import dataclass, asdict
import math
from typing import Callable


@dataclass(frozen=True)
class Config:
    budget: int = 24
    strategy: str = "adaptive"
    seed: int = 1000
    p_fail: float = 0.7
    delta: float = 0.3

    def validate(self):
        if type(self.budget) is not int or self.budget < 0:
            raise ValueError("budget must be a nonnegative integer")
        if self.strategy not in {"adaptive", "uniform", "coarse"}:
            raise ValueError("unknown strategy")
        if not 0 < self.p_fail < 1 or not 0 < self.delta <= 1:
            raise ValueError("invalid failure thresholds")


def interval(failures, n):
    """Wilson interval; descriptive only under adaptive selection."""
    if not n:
        return [0.0, 1.0]
    z = 1.959963984540054
    p = failures / n
    center = (p + z*z/(2*n)) / (1 + z*z/n)
    radius = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / (1+z*z/n)
    return [max(0.0, center-radius), min(1.0, center+radius)]


def diagnose(prefix_count: int, replay: Callable[[int, int], bool], config: Config,
             cancelled: Callable[[], bool] = lambda: False):
    config.validate()
    if type(prefix_count) is not int or prefix_count < 1:
        raise ValueError("a restorable snapshot is required")
    counts = [0]*prefix_count
    failures = [0]*prefix_count
    history = []
    stop = "budget_exhausted"
    error = None
    coarse = sorted({0, min(1, prefix_count-1), prefix_count//2, prefix_count-1})
    initial = [0, 0] + list(range(1, prefix_count))
    for attempt in range(config.budget):
        if cancelled():
            stop = "cancelled"
            break
        if config.strategy == "coarse":
            k, reason = coarse[attempt % len(coarse)], "coarse_round_robin"
        elif config.strategy == "uniform":
            k, reason = attempt % prefix_count, "uniform_round_robin"
        elif attempt < len(initial):
            k, reason = initial[attempt], "initial_coverage"
        elif (attempt-len(initial)) % 5 == 0:
            k = min(range(prefix_count), key=lambda i: (counts[i], i))
            reason = "exploration"
        else:
            p0 = failures[0]/counts[0]
            def priority(i):
                lo, hi = interval(failures[i], counts[i])
                target = config.p_fail if i == 0 else max(config.p_fail, p0+config.delta)
                return (lo <= target <= hi, hi-lo, -i)
            k = max(range(prefix_count), key=priority)
            reason = "threshold_uncertainty"
        # Same prefix and repetition get the same seed in each strategy.
        seed = config.seed + k*100000 + counts[k]
        entry = dict(prefix=k, seed=seed, reason=reason)
        history.append(entry)  # Failed attempts also consume the budget.
        try:
            failed = replay(k, seed)
            if type(failed) is not bool:
                raise TypeError("replay must return a boolean task-failure outcome")
        except Exception as exc:
            stop, error = "environment_error", type(exc).__name__
            entry["error"] = error  # Exception strings may contain private inputs.
            break
        counts[k] += 1
        failures[k] += int(failed)
        entry["failed"] = failed
    rows = [dict(prefix=i, n=n, failures=failures[i],
                 failure_rate=failures[i]/n if n else None,
                 descriptive_interval=interval(failures[i], n))
            for i,n in enumerate(counts)]
    p0 = rows[0]["failure_rate"]
    candidates = [r["prefix"] for r in rows[1:] if r["n"] and p0 is not None
                  and r["failure_rate"] >= config.p_fail
                  and r["failure_rate"]-p0 >= config.delta-1e-12]
    return dict(schema_version=1, config=asdict(config), stop_reason=stop, error=error,
                attempts=len(history), successful_replays=sum(counts),
                coverage=sum(n>0 for n in counts)/prefix_count,
                untested_prefixes=[i for i,n in enumerate(counts) if not n],
                candidate_prefix=min(candidates) if candidates else None,
                conclusion="candidate_requires_confirmation" if candidates else "insufficient_evidence",
                root_cause_confirmed=False,
                interval_scope="descriptive; adaptive sampling; no simultaneous confidence claim",
                prefixes=rows, history=history)
