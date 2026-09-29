# ClarityLink Type-111 transport model — Step 37

## Reusable offline media core

Honda Type-110 media path is now modeled offline:

```text
incremental ScreenStream envelope
  -> optional injected continuous CTR body update
  -> opcode 1: avcC-like SPS/PPS -> Annex-B parameter sets + NAL width
  -> opcode 0: length-prefixed records -> one Annex-B media buffer
                  with pending parameter sets prepended once
  -> timestamp_raw event
```

The code is `HondaScreenReceiverCore` in `src/claritylink-transport/receiver_core.py`. It does not open sockets, derive session keys, pick a Type111 SETUP response, or decode/render. The CTR provider remains injected. Timestamp output remains the raw LE64 header value because Honda's converter timebase is not recovered.

## Type111 compatibility assessment

| Component | Honda Type110 | MHI2 Type111 prior art | ClarityLink reuse status |
|---|---|---|---|
| 128-byte envelope, LE32 body length, opcode | Honda-confirmed | matching family documented in pinned source | **YES as parser candidate**; Honda Type111 itself untested |
| Body AES-CTR and continuous state | Honda-confirmed Type110 | MHI2 reports CTR on its Type111 | **UNKNOWN for Honda Type111**; keep primitive injectable |
| Config as avcC-like | Honda helper parses this layout | MHI2 source/docs identify avcC | **LIKELY reusable**, pending Type111 target verification |
| NAL width and Annex-B | Honda Type110 links avcC width to 1/2/4 callback branches; width 3 unsupported | MHI2 Type111 implements AVCC to Annex-B | **LIKELY reusable**, callback zero-run transform still needs exact modeling |
| Access-unit boundary and timestamp | one ScreenStream message becomes one media buffer; AU semantics high-confidence, converter/timebase unknown | prior-art receiver emits frame samples | **UNKNOWN for Honda Type111** |
| Type111 SETUP contract/listener lifecycle | stock Setup doesn't accept a Type111 handler; unrecognized entries take a log-and-continue path in inspected loop | MHI2 has target-specific interposer | **Type111-specific and unresolved** |

Honda Setup (`0x2854e0`) reads each `streams[]` element's `type` at `0x28590e`. Type 100/101/110 have cases; Type 111 reaches the unknown-type log at `0x2861f6` and then increments the array index/continues at `0x286220`. This proves no Type111 setup branch. It does **not** prove an immediate transaction error; exact overall result depends on surrounding stream entries and later setup state.

## Step 38 boundary

Before any Type111 listener/interposer implementation, recover the Type111 SETUP/security contract and error/rollback behavior. Preserve non-111 entries through stock handling and do not mutate live behavior in this step. Required function map and field checklist: `type111-step38-contract.md`.
