# From replay research to a developer workflow

[English README](../README.md) · [中文首页](../README.zh-CN.md)

## Foundation and scope

Delta-MFP studies when a failed tool-use trajectory enters a reproducible failure regime. Its method restores saved prefixes and compares continuation failure rates with the initial-state rate. This motivates a useful maintenance question: where does additional inspection provide actionable evidence?

The [source README](https://github.com/DaoyuanLi2816/delta-mfp-local-agents/blob/master/README.md) identifies *Before the Fall: Delta Minimal Failing Prefixes for Local Tool-Use Agent Failures* as an accepted **ICML 2026 Workshop on Failure Modes in Agentic AI (FAGEN)** paper, **non-archival**. The venue statement here is attributed to that repository, checked on 2026-09-28. The [OpenReview record](https://openreview.net/forum?id=KAA8FR6fEq) required browser verification during this check. The [workshop website](https://fagen-workshop.github.io/) provides event context.

ReplayHarbor's project and experiments are separately documented. The workshop affiliation belongs to the referenced paper. Published paper results remain separate from this project's simulation and model experiments.

## Product hypothesis

A developer receiving a failure report needs restoration conditions, an affordable next check and evidence another person can verify. The first product boundary therefore covers one restorable environment, explicit budgets and a complete handoff path. Developer time saved and report usefulness are hypotheses awaiting external trials.

The workflow is: select a case → explore within a budget → inspect coverage and uncertainty → confirm a frozen candidate → compare a selected revision → export and independently recompute.

## Implementation and contribution map

| Layer | Implemented role | Inspectable source |
|---|---|---|
| Fixed research dependency | Synthetic tasks, scripted agent, snapshots, replay primitives and provided interventions | [Dependency lock](../upstream.lock.json), [adapter](../src/replayharbor/adapter.py) |
| Budgeted investigation | Uniform, coarse and adaptive exploration; attempts, errors and uncovered prefixes | [core.py](../src/replayharbor/core.py) |
| Evidence interpretation | Fresh fixed-sample confirmation and paired revision comparison with stated assumptions | [validation.py](../src/replayharbor/validation.py), [protocol](statistical-protocol.md) |
| Maintainer workflow | Combine stages and preserve next-action context | [workflow.py](../src/replayharbor/workflow.py) |
| Developer handoff | Case metadata, report, HTML, issue draft, hashes and independent recomputation | [cli.py](../src/replayharbor/cli.py) |
| Real inference boundary | Restore observed history, request new model actions, validate arguments and record a bounded cost ledger | [model_replay.py](../src/replayharbor/model_replay.py) |
| Local product surface | Case selection, cancellation, evidence viewing and completed-bundle download | [workbench.py](../src/replayharbor/workbench.py) |

These are implemented extensions and engineering choices. Algorithmic novelty or superiority requires additional comparison. Existing simulated repairs use explicitly selected dependency-provided interventions; automatic repair synthesis remains outside the current implementation.

## What the experiments changed

**Sampling quality shaped the default.** The [25-case comparison](../experiments/simulation/report.md) exposed weak adaptive behavior. Uniform coverage remains the workbench default, and adaptive exploration is marked experimental. A future policy must improve a frozen evaluation under equal budgets.

**An interface issue shaped the model contract.** The [initial real-model runs](../experiments/deepseek/report.md) exposed a mismatch between natural-language dates and the evaluator's expected format. The revised public contract makes the date explicit while preserving the missing timezone for clarification. This is an interface regression investigation; the changed contract limits performance comparisons.

**Controls made restoration inspectable.** The [fixed-contract experiment](../experiments/deepseek/controlled-failure/report.md) preserved a normal observation, corrupted its timezone answer, and restored the earlier state for fresh clarification. Each condition ran twice. The evidence establishes a small engineering control and guides broader experiments.

**A zero denominator changed the interpretation.** The [reserved task audit](../experiments/heldout/report.md) found no scripted fault branches in the selected execution configuration. The all-normal observations remain useful control evidence; candidate-detection accuracy is undefined. Future evaluation must check fault capability before measuring diagnostic efficacy.

## Next validation decisions

- Freeze a failure-capable suite with normal controls, positive cases and repeated references before comparing policies.
- Observe developers completing installation, evidence interpretation and bundle handoff; record obstacles and denominators using the [trial protocol](developer-trial.md).
- Add an executable external adapter only after specifying state restoration, isolation, error handling and redaction contracts.

## 中文设计摘要

研究启发来自“保存状态后重新执行，观察失败概率如何变化”。ReplayHarbor 将这一思路组织成维护者可使用的预算、证据和交接流程。当前产品价值假设是帮助开发者明确下一步检查内容，并让同事独立核验相同案例。

项目新增贡献可沿代码追踪：调度器决定如何分配复验；确认模块区分探索与新样本证据；问题包连接报告与独立复算；模型适配层明确状态恢复和费用边界；工作台将这些能力串联为操作流程。固定依赖继续提供合成任务和执行基础。

实验记录保留策略效果不足、接口契约修订和评测不适用等发现。这些经验用于选择默认策略、调整任务说明和约束指标结论。后续验证聚焦可触发故障的保留任务，以及真实开发者的首次接入与交接体验。
