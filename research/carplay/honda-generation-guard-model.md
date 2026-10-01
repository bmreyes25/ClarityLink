# Honda-independent project generation guard — 43L.2

Classification: `OFFLINE_PROJECT_IMPLEMENTATION`. This describes project-owned behavior, not Honda lifecycle behavior.

1. Mint an increasing generation for each opaque session identity when a new Setup transaction is observed.
2. Starting a newer generation immediately detaches and idempotently stops any older child associated with that identity. Every commit and cleanup names the full `(identity,generation)` key.
3. Prepare owns only project resources. Mutation/serialization failure rolls back that exact generation. Response-ready is synthetic Honda success only when return code is `0xc8` **and** body-install `statusOut` is zero.
4. Commit rejects stale generations. Honda finalizer and `MC_DEV_CARPLAY_SESSION_DESTROYED` are optional cleanup hints; neither is required.
5. Every prepared or active child has a monotonic project lease. Exact current-generation activity may renew it. A project watchdog reaps expired generations and closes resources exactly once. A configured lease bounds stale-listener lifetime even if HTTP delivery, SessionStart, or Honda finalization is never observed.
6. Expiry values and renewal activity must be selected and validated for the eventual runtime; the offline model deliberately uses injectable clock and synthetic duration. No Honda timeout or event guarantee is inferred.

Guarantees in model: stale rollback cannot mutate a newer Honda response because the model never owns Honda response objects; newer generation wins; cleanup is idempotent; no cleanup depends only on Honda finalization; Honda Type110/audio are outside the registry. Coverage is synthetic; runtime scheduler/callout remains unresolved.
