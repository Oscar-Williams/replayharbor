# Workbench guide / 工作台指南

Follow the README installation in an isolated Python environment. From the repository root run `python -m replayharbor.cli serve --project-root .`, then open http://127.0.0.1:8765 . The web interface currently uses Chinese labels.

| UI label | Action |
|---|---|
| 案例 | Select a built-in case |
| 探索预算 | Set the exploration replay budget |
| 独立确认候选 | Add up to 1024 fixed-sample confirmation replays |
| 修订对照 | Select an upstream synthetic intervention; adds 128 replay pairs |
| 开始复验 / 取消运行 | Run / request cancellation |
| 下载问题包 | Download a completed verifiable bundle |
| 导入报告 JSON | View a local report without executing it |
| 查看真实模型实验 | Read previously recorded model experiments |

Start with calendar_missing_timezone, uniform sampling and budget 24. Enable confirmation and select clarify to exercise the full workflow. Inspect coverage, uncertainty and the next action before downloading. Extract the bundle to a new directory and run `python -m replayharbor.cli verify <directory>`.

Imported reports have unverified provenance. Cancellation preserves partial evidence in memory and disables complete-bundle export. Closing the server clears in-memory jobs; downloaded files remain available. Model-result viewing makes no paid requests.

Windows and WSL need separate environments. An explicit venv interpreter path avoids accidental PATH mixing. venv isolates packages; process environment variables still apply. If GitHub installation fails, a clean local clone at the pinned upstream revision supports `pip install -e <upstream-directory>`. Preserve TLS checks and confirm the revision.

中文操作：选择案例与预算 → 查看覆盖和候选 → 按需独立确认与修订对照 → 下载问题包 → 在新目录复算。每次执行保留独立输出，报告导入用于只读查看。密钥仅用于单独运行的模型实验，网页模拟无需配置密钥。
