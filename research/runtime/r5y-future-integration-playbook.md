# R5Y — future evidence integration playbook

This is a research workflow, **not a deployment guide**. It provides no target commands, binary locations, hooks, authentication, vehicle actions, or permission to run anything on a car.

1. Record a newly available, lawfully reviewable Honda artifact's provenance, build identity, rights, and scope. R5B currently has no analyzable descendant payload.
2. Classify each finding under Rules v2 (`HONDA_STATIC` at most for offline artifact analysis); do not convert model or external prior art into Honda proof.
3. Map each supported claim to one row in the [evidence gap registry](r5y-honda-evidence-gap-registry.md), including ownership, error and cleanup paths. Keep all other rows `UNKNOWN`.
4. Build a host-only fake/replay adapter with invented values first. Run the existing R5Y suite unchanged and add adapter-specific host tests.
5. Review new security, licensing, primary preservation, display warning, cleanup and scope risks. Reassess the controlling R3C decision only through a separate evidence review.
6. Only after all applicable evidence gates and a separate high-risk review could anyone *consider* drafting a future exact vehicle experiment plan. Rules v2 would still require explicit authorization for that plan. R5Y itself authorizes none.

The reusable core is intended to stay frozen during evidence search. A newly discovered artifact should normally change only an adapter contract or host fake and its tests; if the core contract itself changes, record why and rerun all invariant tests.
