# Simulator smoke comparison

Tasks: 25; runs: 225.
No model inference. Fixed strategies; finite-sample reference; engineering smoke scope.

| Budget | Strategy | Candidate agreement | Mean coverage |
|---|---|---|---|
| 12 | uniform | 25/25 | 100.0% |
| 12 | coarse | 25/25 | 95.2% |
| 12 | adaptive | 25/25 | 100.0% |
| 24 | uniform | 25/25 | 100.0% |
| 24 | coarse | 25/25 | 95.2% |
| 24 | adaptive | 25/25 | 100.0% |
| 48 | uniform | 25/25 | 100.0% |
| 48 | coarse | 25/25 | 95.2% |
| 48 | adaptive | 0/25 | 100.0% |

Agreement includes both methods returning no candidate. It does not establish diagnostic accuracy or root cause.
Follow-up: held-out task templates, repeated references, independent confirmation, and real-model adapter validation.
