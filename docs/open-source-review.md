# Open-source delivery references

Reviewed 2026-09-28. These projects inform repository organization; their scale and performance claims are specific to their own products.

| Reference | Observed practice | ReplayHarbor application |
|---|---|---|
| [Promptfoo](https://github.com/promptfoo/promptfoo) | Runnable quick start, examples, CLI and evaluation workflow | Lead with a no-key synthetic example and verification command |
| [Langfuse contribution guide](https://github.com/langfuse/langfuse/blob/main/CONTRIBUTING.md) | Development prerequisites, validation commands and contribution paths | Document local tests, browser checks and issue-to-change workflow |
| [Ruff contribution guide](https://github.com/astral-sh/ruff/blob/main/CONTRIBUTING.md) | Explicit development and testing guidance | Keep contributor setup and focused regression checks discoverable |

The public package includes language-linked READMEs, license and attribution, evidence boundaries, security reporting, CI, structured issues and contribution guidance. Existing synthetic experiment failures remain visible. Large-project infrastructure is added only when the workflow needs it.
