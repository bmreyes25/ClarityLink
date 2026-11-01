# Honda experiment workflow

This entry replaces the former multi-stage approval runbook. Use the
[three-level experiment workflow](../safety/experiment-risk-levels.md) for
scope, review, and one session-level owner decision, and
[vehicle-testing.md](../safety/vehicle-testing.md) for practical readiness,
stop, privacy, and restoration requirements.

The C-P capture and its approval remain historical and untouched. The separate
comprehensive Type111 evidence plan is described in the
[current campaign status](../diagnostics/comprehensive-runtime-campaign.md);
its fixed live backend is available only behind exact private session
authorization. The unchanged Phase 0/1 identity check is Level 1 and requires a
fresh owner session decision; transition and diagnostic phases add only the
technical or qualified safety review required by their risk. No current scope
has owner session authorization, so there is no session to start.
`safeForHonda() == false` and deployment remains unauthorized.
