# Active architecture decision — Step 42B

## Selected target

**JMCS-integrated control plane and Type111 receiver, with an ExternalDisplay-host renderer adapter.** Keep the stock Honda Type110 code path first and unchanged; handle a prospective Type111 request and listener in ClarityLink-owned state; pass decoded frames to the existing ExternalDisplay View host through a separately designed bounded IPC or same-process renderer adapter. This uses the current receiver session owner for Setup/security state and the existing display owner for output.

This is the target architecture, **not a deployment-ready design**. Honda Type111 schema/security compatibility, a supported ExternalDisplay frame handoff, and a safe code-entry seam into jmcs are all unresolved. `LD_PRELOAD` is parked as a fallback seam only. No Type111 field or key behavior is promoted from MHI2 to Honda.

## Current active execution mode

Until those gates change, active work is the **host-only HondaOS digital twin and evidence-labeled Type111 models**. No companion test, live Type111, boot change, or jmcs no-op load test is authorized or ready from current evidence.

## Target flow

```text
iPhone
  -> Honda jmcs: existing /info and Setup transaction
      -> stock Type110 unchanged
      -> ClarityLink Type111 handler after stock behavior (future)
          -> separate listener/security/receiver state (future)
              -> bounded frame handoff (interface not yet designed/proven)
                  -> ExternalDisplayOutService View host (requires host-side entry)
```

## Why this wins over external proxy now

The proxy option has no known traffic-redirection point, no classified phone/jmcs TCP channel, and no way in the reviewed interfaces to receive the receiver-session master material. A proxy may be possible with new endpoint/authentication work, but existing evidence does not show a smaller or safer seam. The in-process design at least places the proposed second-stream handler next to the original Setup request/response and screen KDF. It remains gated on how code would enter jmcs.

## Architecture gates

| Gate | Current state |
|---|---|
| Honda Type110 baseline | Well recovered statically; no runtime modification |
| Honda Type111 request/response | No handler/response; iPhone request behavior unknown |
| Session key access outside jmcs | Not found |
| jmcs entry method | Not proven; preload parked |
| ExternalDisplay renderer host | Confirmed, same-process View hierarchy |
| Supported ExternalDisplay frame API | Not found |
| Host-only test suite | Passes; synthetic only |
| Live readiness | Not ready |

The selected target can be revisited only when one of the explicit gates is resolved with Honda-specific evidence.
