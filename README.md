# ReplayHarbor

**Budget-aware agent replay, evidence review, and reproducible developer handoff.**

English · [简体中文](README.zh-CN.md)

[![CI](https://github.com/Oscar-Williams/replayharbor/actions/workflows/ci.yml/badge.svg)](https://github.com/Oscar-Williams/replayharbor/actions/workflows/ci.yml)
[![MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

An agent failure report becomes actionable when a maintainer can inspect the restored state, understand the evidence, and reproduce the result. ReplayHarbor connects these steps in a local workbench and CLI.

**Status: experimental, local-first.** The runnable workflow covers 25 built-in synthetic cases. A bounded DeepSeek adapter exercises fresh model inference over a restored synthetic environment. External reports support read-only viewing. The workbench currently uses Chinese labels; CLI and core evidence fields use English.

![ReplayHarbor workbench showing prefix coverage and replay evidence](docs/assets/workbench.png)

## Start with a reproducible case

Requirements: Git and Python 3.11. No GPU or API key is needed for this example. Choose a local directory with space for an isolated environment.

```bash
git clone https://github.com/Oscar-Williams/replayharbor.git
cd replayharbor
python -m venv .venv
```

Activate it with `.venv\Scripts\Activate.ps1` on Windows PowerShell, or `source .venv/bin/activate` on macOS/Linux. Install the pinned upstream environment and ReplayHarbor:

```bash
python -m pip install "delta-mfp-local-agents @ git+https://github.com/DaoyuanLi2816/delta-mfp-local-agents.git@c01fbafca01d34e5e7492d48f856d75bf6f7b8ec"
python -m pip install -e .
python -m replayharbor.cli demo --strategy uniform --budget 24 --out artifacts/first-case
python -m replayharbor.cli verify artifacts/first-case
python -m replayharbor.cli serve --project-root .
```

Open **http://127.0.0.1:8765** for the workbench, or `artifacts/first-case/index.html` for an offline report. Verification checks file hashes and independently recomputes the synthetic result. Use a new output directory for each run.

## From a failure to a handoff

1. **Explore within a budget.** Compare uniform, coarse and experimental adaptive sampling across saved prefixes. Inspect uncovered positions and descriptive uncertainty.
2. **Confirm a frozen candidate.** Use fresh fixed-size samples to examine the failure-rate increase relative to prefix zero.
3. **Compare a selected revision.** Evaluate an upstream synthetic intervention using paired seeds and an explicit effect interval.
4. **Hand over evidence.** Export JSON, HTML, an issue draft and a hash manifest. Another developer can recompute the same case.

```bash
python -m replayharbor.cli demo --strategy uniform --confirm-n 512 --confirm-budget 1024 --repair clarify --compare-n 128 --compare-budget 256 --out artifacts/confirmed
python -m replayharbor.cli verify artifacts/confirmed
```

This example budgets 24 exploratory, 1024 confirmation and 256 revision replays. `clarify` is an explicitly selected upstream simulator intervention. Cancellation preserves partial evidence locally; completed runs support verifiable bundle export.

## Design choices that matter

| Decision | What it makes inspectable |
|---|---|
| Separate exploration and confirmation | Adaptive observations and fixed-sample evidence have distinct interpretations |
| Track every attempted replay | Errors and exhausted budgets remain visible in the cost of diagnosis |
| Restore state, then execute | Saved-output playback and fresh execution have explicit boundaries |
| Verify the report by recomputation | Integrity checks and executable evidence support developer handoff |
| Keep evaluation labels outside the scheduler | Sampling decisions receive prefix counts and observed outcomes |

A candidate identifies a failure-rate association. Earliest failure position and causal root cause require further evidence. See the [architecture](docs/product-and-architecture.md) and [statistical protocol](docs/statistical-protocol.md).

## Evidence and current limits

- **25-case simulation:** 225 exploratory runs compare three strategies at three budgets. Results include weak adaptive performance and remain available in the [experiment record](experiments/simulation/report.md).
- **Real inference controls:** two normal continuations succeeded, two corrupted-timezone continuations failed, and two rollbacks followed by clarification succeeded. These six synthetic episodes used 20 model calls. [Protocol and results](experiments/deepseek/controlled-failure/report.md).
- **Evaluation audit:** 16 reserved tasks exposed an all-normal scripted execution contract. Candidate-positive reference count was zero; diagnostic accuracy is undefined for that run. [Audit](experiments/heldout/report.md).

These are engineering checks. Broad efficacy, natural user failures and support-time savings need further evaluation. Fresh real-model responses may vary; the deterministic bundle verifier applies to synthetic scripted runs.

## Use and contribute

- [Workbench guide](docs/workbench.md) · [Optional DeepSeek setup](docs/deepseek-setup.md)
- [Contributing](CONTRIBUTING.md) · [Report a workflow issue](https://github.com/Oscar-Williams/replayharbor/issues/new/choose)
- [Security policy](SECURITY.md) · [Roadmap](docs/roadmap.md) · [Changelog](CHANGELOG.md)

The workbench binds to loopback and runs built-in cases. Model experiments use a separately configured local credential and capped requests. Review exported content before sharing.

## Attribution and license

Created and maintained by **Oscar-Williams**, with AI-assisted implementation and documented experiments. [Delta-MFP](https://github.com/DaoyuanLi2816/delta-mfp-local-agents) by Daoyuan Li supplies the synthetic environment, scripted agent and replay primitives. ReplayHarbor adds scheduling, evidence semantics, confirmation, handoff verification, model adaptation and the workbench. See [third-party notices](THIRD_PARTY_NOTICES.md) and [upstream lock](upstream.lock.json).

Licensed under [MIT](LICENSE). Upstream copyright and license are preserved.
