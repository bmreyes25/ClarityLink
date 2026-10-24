# CL-T111-INGEST-01: offline Type111 ingest into the lease-gated Display 1 fail-safe

Status: implemented and tested **offline, on synthetic lab content only**.
Depends on PR #92 (CL-INT-03 fail-safe). Governed by the canonical goal in
PR #93 (`docs/project/primary-goal.md`, pipeline stages and the five evidence
categories) and the offline policy in PR #91. `safeForHonda()` stays `false`.

## What this is, and is not

It connects three things that already existed but were never joined:
the Type111 `Receiver` (framing, security provider, avcC/Annex-B, FFmpeg
decode, per-stream dispatcher), and the CL-INT-03 `Display1LeaseHost` /
`FailSafeCoordinator`. It is **not** a navigation UI, a map renderer or a Display 0
mirror; the sink is content-agnostic and never inspects what the pixels depict.

```
locally generated H.264 (SYNTHETIC_LAB_CONTENT)
  -> lab Type111 framing (CURRENT_IOS_TYPE111 profile; VideoConfig avcC + AVCC access units)
  -> Receiver.receive_secondary_frame   framing -> ClearLabSecurity -> avcC/Annex-B -> FFmpegDecoder (PNG)
  -> PerStreamFrameDispatcher worker    bounded (2 frames), stream/generation fenced
  -> LeaseGatedOutput.show              png_to_rgb24 -> VideoFrame -> LeaseBoundFrame
  -> FailSafeCoordinator.submit_frame   lease, epoch, strictly increasing sequence
  -> Display1LeaseHost -> SimulatedClusterHost   (simulated Display 1)
  -> disconnect / fault: revoke first, then independent cleanups
```

## Evidence classification (kept separate)

| Category | Status |
|---|---|
| Synthetic lifecycle | **Established offline** (this doc's tests) |
| Type111 protocol handling | **Established for generated lab bytes only**; the framing profile is a lab hypothesis |
| iPhone-origin video | **UNVERIFIED** - no real iPhone bytes were processed |
| Honda receiver integration | **UNVERIFIED** |
| Physical Display 1 output | **UNVERIFIED** |

## Interface map (verified against source)

| Piece | Where | Role here |
|---|---|---|
| Framing profiles | `claritylink_jmcs/media.py` | `CURRENT_IOS_TYPE111` selected explicitly; Type110 profile is not relabelled |
| Security | `security.py` | `ClearLabSecurity` only when `lab_mode`; `EvidenceRequired*` fail closed |
| Decoder | `decoder.py` | unchanged; emits PNG `DecodedFrame` |
| Dispatcher | `stream_dispatch.py` | unchanged; sink is `LeaseGatedOutput` |
| Canonical frame | `frames.py` (new) | `VideoFrame` RGB24 + `png_to_rgb24` boundary |
| Bridge | `src/claritylink-honda/type111_ingest.py` (new) | `LeaseGatedOutput`, `Type111IngestPipeline`, fault map |
| Fail-safe | `failsafe_coordinator.py` | unchanged except read-only `lease` / `sequence` properties |

## Canonical frame contract (`frames.py`)

`VideoFrame`: immutable; `pixels` (bytes, RGB24), `width`, `height`, `stride`
(= width*3, no padding), `timestamp`, `session_generation`, `stream_type`,
`stream_connection_id`, `stream_generation`, `provenance`
(`SYNTHETIC_LAB_CONTENT` is the only value that exists). Bounds: see
`MAX_FRAME_PIXELS` / `MAX_FRAME_BYTES` in `frames.py`, validated in
`__post_init__`. PNG, RGB24 and compressed H.264 are never interchangeable: the
single conversion is `png_to_rgb24` (8-bit non-interlaced RGB/RGBA, chunk order
and CRC checked, inflate capped by the header's promise, alpha dropped not
composited). The host holds a `LeaseBoundFrame` (frame + lease epoch + lease
generation + sequence). Ownership: the frame owns its bytes; the host keeps
only the latest frame; teardown drops it.

## Fault mapping (`classify_receiver_code`)

The receiver tears the secondary stream down on **every** media-path error
except a stale decoder, so the classification decides the fault, not whether
the stream survives.

| Receiver / sink outcome | Result |
|---|---|
| `stale_secondary_decoder` (the only error the receiver survives without tearing the stream down) | reject frame only, lease kept |
| decoder codes (`decode_failed`, `decoder_closed`, bad decoded dimensions) | `DECODER_DEATH` |
| EOF/read failure, malformed framing/AVCC, security refusal, lease/sink refusal, **unknown codes** | `TYPE111_TRANSPORT_FAILURE` (fail closed) |
| unexpected non-receiver exception | `RECEIVER_DEATH` (whole session torn down) |
| setup refusal / partial setup / grant refused | `INIT_FAILURE` |
| `disconnect(USB_UNPLUG / CARPLAY_ENDED)` | whole receiver session torn down |
| factory interrupt, display restart | `FACTORY_WARNING`, `DISPLAY_HOST_RESTART` |

Order is always: hide host content (`fail_closed` / `host.revoke`), then the
coordinator runs each cleanup independently. A cleanup that raises is reported
in `CleanupReport.failed`, recorded in `cleanup_failures`, stays visible in
`residual()`, and never blocks revocation or the other cleanups. A late fault
never raises the link state.

## Known limits and open gaps

- **Lease expiry is lazy and adopted by `tick()` in the producer process.** The
  host hides expired content on its own (proved with no pipeline call), but
  releasing receiver resources needs `tick()`/`heartbeat()`. Guaranteed
  host-owned withdrawal when the producer is dead is **CL-INT-04, still open**.
- A truncated-but-parseable H.264 slice can be decoded by FFmpeg's error
  concealment and presented; decode success is not stream integrity.
- `png_to_rgb24` is pure Python: observed ~157 ms median at 800x480, the
  dominant host cost (FFmpeg decode+scale ~36 ms). Frame size is capped so a
  crafted frame cannot stall the sink for long; not otherwise optimised. An
  Android path would take raw output from MediaCodec, which is unimplemented.
- Synthetic authentication and clear media exist only behind `lab_mode`;
  `lab_mode=False` refuses to open a session and the sink refuses all frames.
  `lab_mode` is a constructor flag, not an attestation.
- The control API is single-threaded; the dispatcher worker is the only other
  thread and cleanup requested from it is deferred to the control thread.
- Not done and not claimed: real iPhone Type111 bytes or authenticated context,
  Honda receiver modification, Android/Honda decoder integration, factory
  Navigation restoration proof, independent rollback proof.

## Tests

`tests/integration/test_cl_t111_ingest_01_{e2e,faults,frames,metrics}.py`, with
generated input in `t111_synth.py`. They drive the real `Receiver`, real
FFmpeg and the real coordinator; the simulated cluster host is the only
simulation. Measurements are observations of one host, not acceptance
thresholds.
