# Independent restoration verifier — 43T1-PREP2

**Decision: `RESTORATION_VERIFIER_MODEL_READY`.** The verifier is `verify_restoration` in `src/claritylink-honda/prep2_runtime.py`; it has a distinct immutable `RestorationFacts` input and no installer success flag or shared mutable installer state.

It returns `RESTORED_TO_VERIFIED_STOCK` only when all fresh observations match exact stock callsite bytes, surrounding context, BL target and continuation, and show no project generation, listener, accepted FD, worker, or bridge. Stale/mismatching/incomplete facts yield `RESTORATION_NOT_PROVEN`; non-applicable yields `NOT_APPLICABLE`.

The PREP2 integration test builds the facts after local resource close and simulated detach. This is `LAB_SYNTHETIC_CONFIRMED`, not an independent Honda process read or post-reboot observation.

## Future post-reboot observational checklist

After a separately reviewed modifying experiment only: verify center Display Audio, stock CarPlay, audio, and cluster pages behave normally; verify target process identity; observe stock callsite bytes and surrounding context; prove project generation/listener/socket/worker/bridge absent; then record reboot and post-reboot stock evidence. This checklist is not executed or authorized by PREP2.
