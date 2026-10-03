# Independent restoration verifier — 43T1-PREP2

**PREP2 status (historical): `RESTORATION_VERIFIER_MODEL_READY`. R1 status: verifier contract strengthened; target restoration remains unproven.** The verifier is `verify_restoration` in `src/claritylink-honda/prep2_runtime.py`; it has a distinct immutable `RestorationFacts` input and no installer success flag or shared mutable installer state.

R1 additionally requires expected and observed address equality, Thumb alignment, exact stock instruction sequence and SHA-256, an explicit rollback-completed fact, at least two separately recorded exact readback observations (first `RESTORED`, subsequent `ALREADY_RESTORED`), and a fresh final readback after interruption. Stale/mismatching/incomplete facts yield `RESTORATION_NOT_PROVEN`; non-applicable yields `NOT_APPLICABLE`. The R1 records are verifier inputs in tests, not real process reads. The verifier never writes memory and cannot prove that a future reader is independent or truthful.

The PREP2 integration test builds the facts after local resource close and simulated detach. This is `LAB_CONFIRMED`, not an independent Honda process read or post-reboot observation.

## Future post-reboot observational checklist

After a separately reviewed modifying experiment only: verify center Display Audio, stock CarPlay, audio, and cluster pages behave normally; verify target process identity; observe stock callsite bytes and surrounding context; prove project generation/listener/socket/worker/bridge absent; then record reboot and post-reboot stock evidence. This checklist is not executed or authorized by PREP2.
