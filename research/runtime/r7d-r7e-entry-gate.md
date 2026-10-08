# R7D to R7E entry gate

R7E preparation stays closed until R7D passes its full offline simulation acceptance and exact-head hosted checks. R7E may prepare separately authorized plans only; R7D does not authorize Honda execution.

Required R7D evidence: R7C regressions; 30-minute long run; memory/resource trend; measured throughput and latency; 100 Type111 restarts; display recreation; network recovery; decoder stress; 500-session churn; project-owned restoration; observability audit; explicit Honda question matrix; repository suite/sanitizers; repository health; diff check; exact-head Offline CI and CodeQL.

Current decision pending final repository/hosted gates: all local runtime, fault, churn, restoration, observability, repository suite, sanitizer, ARMv7/import, health, and diff checks pass. The 30-minute run sustained 14.405 FPS against the 30 FPS target; this performance gap is documented. Exact-head Offline CI and CodeQL and the R7D PR remain required before opening R7E entry. R7E entry remains `CLOSED` until those checks pass.
