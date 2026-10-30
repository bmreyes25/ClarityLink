# HondaHack and CL-R12 rendering architecture comparison

**Status:** offline architecture comparison; no vehicle or Honda display testing. `safeForHonda() == false`.

HondaHack 7.7.7 and ClarityLink’s CL-R12 synthetic path have different inputs, transport stages, and owners. HondaHack captures an Android display and mirrors its pixels into a factory host View. CL-R12 begins with synthetic Type111 media in an offline receiver model, then verifies, decodes, converts, and delivers frames to a laboratory renderer. Neither path proves that Honda accepts arbitrary third-party Type111 frames.

## Stage comparison

| Stage | HondaHack 7.7.7 | CL-R12 synthetic path | Cost or unknown |
|---|---|---|---|
| Source | Display 0 screenshot | Synthetic Type111 H.264 access units | Capture versus network/media parsing are not comparable workloads. |
| Source dimensions | 400×240 ARGB bitmap | 800×480 lab output target | Different pixel count, format stage, and output assumptions. |
| Offered cadence | Saved low nominal preference; not a sustained FPS result | 30 FPS offered lab workload | A preference or offered rate is not delivered-rate evidence. |
| IPC | Memory-backed data, duplicated descriptor, Messenger | MemoryFile/PFD/Messenger in the synthetic receiver lab | Both use shared-memory/FD IPC; ownership, framing, generation checks, and payload differ. |
| Processing | Screenshot, buffer copy, bitmap reconstruction, fit-to-view scaling | Input validation, H.264 parsing, decode, frame verification, conversion, and View delivery | CL-R12 adds decode and verification work; HondaHack captures already-rendered pixels. |
| Output | View/ImageView attached inside a privileged factory host process | Synthetic lab View owner | HondaHack’s host capability is private and has no supported third-party contract. |
| Failure proof | Limited historic observations and static cleanup path | Synthetic failure and lifecycle tests | Neither synthetic nor static evidence proves Honda warning priority or restoration. |

A 400×240 capture contains 96,000 pixels, one quarter of an 800×480 frame’s pixel count. That arithmetic does not establish relative speed: capture, IPC copies, decode, scaling, UI scheduling, and host composition differ, and no equivalent benchmark was run in this research pass.

## Decision implications

- Do not replace CL-R12’s synthetic input or IPC based on HondaHack’s working mirror.
- Do not infer sustained 30 FPS capability from HondaHack’s configured cadence.
- Compare performance only with equivalent resolution, format, offered cadence, timing boundaries, queue depth, and failure handling.
- Track capture, copies, allocation, decoder, conversion, Binder/FD lifetime, UI invalidation, and stale-frame behavior as separate stages.
- Treat the factory host View path as a research precedent, not an adapter contract.
- Retain the Honda integration NO-GO until an OEM-supported frame-admission interface and lifecycle/safety contract are established.

## Evidence and limits

The HondaHack source and geometry distinction are summarized in the [display-path report](hondahack-display-path.md). CL-R12’s synthetic boundary is described in the [Type111 renderer handoff contract](../display/type111-renderer-handoff-contract.md). The factory host and private API boundary are assessed in the [CL-HH-07 architecture report](cl-hh-07-deep-architecture-analysis.md). The 30 FPS figure is a synthetic offered workload, not a Honda measurement. No native frame-admission, Honda Type111, or equivalent performance benchmark is established.
