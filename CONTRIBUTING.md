# Contributing

Welcome reproducible bug reports, clearer documentation, synthetic fixtures and focused code changes. Describe the developer task and the decision your change improves. Discuss changes to statistical semantics or external adapters in an issue before substantial implementation.

## Development

Follow the isolated-environment installation in the README, then install `python -m pip install pytest==9.1.1`. Run:

```bash
python -m pytest -q
python scripts/check_secrets.py
python -m replayharbor.cli verify examples/confirmed-case
git config core.hooksPath .githooks
```

Hooks are a local guard; CI also runs the scanner. Tests use synthetic fixtures and mocked provider responses. Paid model experiments require explicit local configuration and stay outside CI.

For a pull request, explain the user problem, resulting behavior and validation. Include a regression test when behavior changes. Check workbench changes in a browser. Preserve existing experiment outputs; new experiments need a protocol written before execution, source revision, budgets and honest denominators.

Keep credentials, personal traces, machine paths and private planning notes out of commits. Retain upstream licenses. AI-assisted contributions are welcome: review the resulting code, understand its behavior and disclose relevant assistance in the PR. Contributors remain responsible for their changes.

## Review expectations

Small, inspectable changes are easier to review. Distinguish observed outcomes, statistical assumptions and proposed improvements. A reproducible inconclusive result is useful. Maintainers may request a smaller scope or additional evidence. Participation follows the [code of conduct](CODE_OF_CONDUCT.md).
