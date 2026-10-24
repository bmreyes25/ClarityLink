# ClarityLink architecture

## Goal

> **PRIMARY GOAL: iPhone-origin Type111 secondary CarPlay video on factory Display 1, simultaneous with normal Type110 on Display 0.** See the canonical [primary goal](../project/primary-goal.md) for non-goals and the ten-stage traceability matrix.

Keep factory CarPlay on the Honda Clarity center display while the connected iPhone's genuine secondary CarPlay video, delivered over Type111, is presented in the instrument cluster's existing Navigation region. What that video shows is decided by iOS and the app, not by ClarityLink; no particular app output (for example Apple Maps or Waze) is promised, and ClarityLink does not draw its own navigation. Other stock safety and cluster content must remain intact.

## Evidence-backed architecture boundary

Apple documents independent vehicle-system CarPlay display streams. Honda's archived receiver evidence confirms its Type110 path and confirms that unsupported Type111 is currently skipped. The architecture below is therefore a target, not a working Honda Type111 implementation.

```mermaid
flowchart LR
  iPhone[iPhone] --> session[Authenticated CarPlay session]
  session --> jmcs[Honda jmcs]
  jmcs -->|Honda-confirmed stock Type110| center[Stock center display]
  jmcs -.->|proposed Type111 integration; not implemented| cl[ClarityLink Type111 state]
  cl -.->|modeled ScreenStream / H.264| renderer[Renderer adapter]
  renderer -.->|real handoff unknown| host[ExternalDisplay host]
  host --> cluster[Instrument-cluster Navigation region]
```

## Invariants

- Honda stock Setup runs first in the target design.
- Type110 response, listener, crypto state, display behavior, and audio remain stock-owned.
- Type111 state is independent; its failure must not disturb Type110.
- Current Type111 response fields, display correlation, security behavior, and iPhone trigger are unknown for Honda.
- The offline twin's H.264 media and renderer frames are synthetic values; they do not prove Honda wire acceptance or the ExternalDisplay handoff.

## State separation hypothesis

Keep three candidate domains separate: (1) Type111 transport/listener lifetime, (2) UI ownership and selected content, and (3) ViewArea/cluster geometry. This decomposition is informed by external MHI2 prior art and is a `HYPOTHESIS` until Honda evidence verifies it.

## Pointers

- [Source-pinned prior art](../research/carplay-altscreen-prior-art.md)
- [Honda-specific research plan](../research/honda-type111-research-plan.md)
- [Current state](../../PROJECT_STATE.md)
- [Next technical action](../../NEXT_ACTION.md)
