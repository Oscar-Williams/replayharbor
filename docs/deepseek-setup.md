# Optional DeepSeek configuration

Copy `.env.example` to `.env` in the repository root and enter your own credential in a local editor. Install the project first; python-dotenv is included. Use an account with a suitable spending limit.

Fields: `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL` and `DEEPSEEK_MODEL`. Process variables take precedence over the explicitly selected project's `.env`. The supported endpoint is official HTTPS; the current experimental adapter and recorded rate card target deepseek-flash.

```bash
python -m replayharbor.cli check-config
python -m replayharbor.cli probe-model
python -m replayharbor.cli model-smoke --task-contract explicit-date-v2 --out artifacts/model-run.json
```

check-config reports credential presence without displaying its value. probe-model requests the model list; adding --completion makes one short inference. model-smoke makes paid requests with at most 24 calls and a USD 0.10 reservation cap. Recorded prices are dated estimates; check the [provider documentation](https://api-docs.deepseek.com/) before a new run. The adapter only executes synthetic tools.

Keep `.env` private and enable hooks with `git config core.hooksPath .githooks`. Run `python scripts/check_secrets.py` before sharing changes. Provider responses are nondeterministic; each new experiment needs a new output path. See the [model protocol](real-model-protocol.md).
