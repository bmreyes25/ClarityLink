# R7C1 Surface lifecycle closure

`SurfaceSinkCore` is the host-testable implementation behind `AndroidSurfaceSink`. It owns the generation, stream, and surface token tuple; validates RGBA dimensions, source stride and exact byte count; requests the configured native window geometry; validates destination dimensions/stride/byte bounds; copies rows; and always posts after a successful lock. Invalidation serializes against a frame operation, marks the sink invalid, and releases its backend reference. Later frames and clears fail closed. Replacement uses a new sink/token; the old sink stays invalid.

`AndroidNativeWindow` implements the narrow `SurfaceWindow` boundary with API17 `ANativeWindow_setBuffersGeometry`, `lock`, `unlockAndPost`, `acquire`, and `release`. API17/ARMv7 build and symbol audit passed. No real Android Surface or ANativeWindow runtime was available.

## Verification

- `native/tests/surface_sink_core_test.cpp`: attach identity, wrong generation/stream, row copy with padding, clear, bad source stride, zero/oversized dimensions, geometry/lock/post failure, invalidation twice, replacement token, and a condition-variable-controlled frame/invalidation race.
- `native/tests/r7c1_integrated_adapter_test.cpp`: real decoder output enters `SurfaceSinkCore` for Type110 and Type111 in distinct host fake buffers; both are cleared at teardown. A secondary surface failure leaves Type110 working.
- Normal, ASan/UBSan, and TSan host runs passed. Evidence: `HOST_SIMULATED_ANDROID_RUNTIME` / `IMPLEMENTED_OFFLINE`.

## ECC findings

| Finding | Risk | Fix | Verification |
|---|---|---|---|
| Frame teardown used generation 0 in the receiver Stream destructor, so a generation-valid sink could reject clear. | Stale output after stream close. | Store owner generation per Stream and clear with that exact generation. | Integration asserts both surfaces zero after every one of 100 cycles. |
| Android window copy logic could not be host tested independently of Android symbols. | Arithmetic and lifecycle regressions untested. | Extract `SurfaceSinkCore` and `SurfaceWindow`; production Android adapter continues to call API17 ANativeWindow functions. | Host fake lifecycle tests plus API17 ARM compile/import audit. |
| Replacement or removal racing with frame delivery might release the backend during a copy. | Use-after-release. | One core mutex serializes presentation, clear, and invalidation; no Java callback is made under it. | Deterministic CV-controlled invalidation test and TSan. |
| Pixel stride could be confused with byte stride. | Out-of-bounds/row corruption. | Treat Android buffer stride as pixels; checked multiply by four and bounded row copies. | Padded-stride byte assertions and malformed dimension/stride tests. |

Limit: these tests execute the production state/copy core with a fake backend, not Android's actual window locking or compositor behavior.
