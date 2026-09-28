# Security

ReplayHarbor is an experimental local tool. The workbench binds to 127.0.0.1 and supports built-in synthetic execution. Keep it on a trusted machine; network hosting needs an additional authentication and isolation design.

Credentials belong in a local `.env` or process environment. `.env.example` contains empty credentials. Provider requests use approved HTTPS endpoints; browser routes do not accept model keys or initiate paid runs. Reports and imports remain untrusted data; review them before sharing.

## Report a vulnerability

Use [GitHub private vulnerability reporting](https://github.com/Oscar-Williams/replayharbor/security/advisories/new). Include affected revision, a synthetic reproduction, impact and suggested mitigation. Keep credentials, personal traces and exploit details in the private report. If the private form is unavailable, open a minimal issue asking for a private contact channel and omit vulnerability details.

Security fixes target the current main branch. There is no response-time guarantee. Rotate any credential that has been disclosed and remove it from affected histories; ignoring a file only prevents future accidental additions.

## Implemented boundaries

Host and same-origin token checks, restrictive content policy, fixed asset routes, case whitelist, bounded inputs, secret-pattern scanning of working files/index/history, and pre-export inspection reduce common failure paths. Pattern scanning is a focused guard; human review remains necessary. API experiments transmit the synthetic task and action history to the configured provider.
