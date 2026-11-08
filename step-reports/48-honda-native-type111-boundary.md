# CL-48 — Honda native Type111 feasibility boundary

**Verdict: `CL-48 — EXACT UNSOLVED NATIVE CONTRACT`.** Publicly reviewable material still does not establish a supported Honda Type111 delegation contract. `HONDA TYPE111 INTEGRATION — NOT PROVEN`; `safeForHonda() == false`.

## Public engineering result

The experiment hypothesis was that a narrowly bounded ARM32 emulator harness can determine whether a fingerprinted shared object’s selected callback-registration routine obeys its advertised Thumb entry, AAPCS argument placement, callback-table copy, return, and registration-flag behavior, without involving Honda runtime or the prior Type111 transaction model. Falsifiable acceptance required: reject malformed or mismatched ELF identity; enforce executable function and writable object ranges; reject inconsistent dynamic metadata, unsupported relocations, invalid symbol references, and out-of-range execution; invoke with two distinct six-word synthetic tables; distinguish correct first/second return and copy behavior; require the initial registration flag to be zero and the callback table to differ from the first input; require the flag to become one after the first call and remain one after the second; require callback storage and flag objects not to overlap; and repeat setup in fresh emulator instances. Failure of any safety precondition or mismatch in observed behavior is a failed probe, not a compatibility result.

The CL-48 work added a bounded ARM32 ELF callback-registration probe and focused tests. The probe verifies a caller-supplied SHA-256, rejects non-ARM32/LE/ET_DYN inputs, resolves caller-selected symbols, supports only section-described `R_ARM_RELATIVE` and `R_ARM_JUMP_SLOT` relocations, and fails closed when any active dynamic relocation table lacks an exact matching section by address, size, and type, or when `DT_TEXTREL`, `DF_TEXTREL`, `DT_RELR`, or Android packed relocations are present. It reads relocation entries and imported dynamic-symbol records from file-backed `PT_LOAD` mappings, validates Thumb function and executable PLT bounds, and caps PLT size both absolutely and in relation to the dynamic jump-slot count. Execution uses synthetic callback pointers under a per-call instruction budget and is refused outside the selected function/PLT ranges and local import/return stubs; ARM-state execution is permitted only within the validated PLT range. Undefined imports use a local zero-return stub; defined-symbol PLT calls are rejected. It contains no target paths, fingerprints, symbols, addresses, or firmware bytes. Its caller-supplied digest verifies content identity only; it does not authenticate source provenance or authorize analysis.

For Honda-native integration, the public evidence classification remains `UNKNOWN`. The new public synthetic ELF tests are `SYNTHETIC_MODEL_ONLY`. A separate private native-artifact exercise used Unicorn instruction emulation with local zero-return import stubs; it did not execute in a Honda process or on Honda hardware. Its artifact-derived observations and implementation details are retained in private local research under the repository's publication policy and are not reproduced or reproducible from this public change. No proprietary implementation behavior is claimed in this report, and the private exercise does not prove Honda runtime behavior, Type111 acceptance, phone behavior, authentication, protected media ownership, or display output.

## Reproducible public-source validation

The focused tests include actual execution of short synthetic Thumb functions in Unicorn, plus parser/layout tests and the existing negotiation regressions. No archived Honda artifact is needed for this public test command:

```text
python -m pytest -q tests/honda/test_native_boundary_probe.py \
  tests/negotiation/test_setup_contract.py \
  tests/negotiation/test_type111_setup_contract.py \
  tests/negotiation/test_existing_call_wrapper_contract.py
```

Results on the current final-source candidate: **57 probe tests passed**; combined focused regressions **112 passed, 21 subtests passed**. `python -m compileall -q tools/honda_native_boundary_probe.py tests/honda/test_native_boundary_probe.py` and `git diff --check` passed. A handcrafted synthetic ELF32 ARM shared object with real `PT_DYNAMIC` tags and file-backed relocation tables exercises image mapping, `R_ARM_RELATIVE` and `R_ARM_JUMP_SLOT`, executable PLT loading, symbol resolution, and a synthetic Thumb registration routine. Separate bounded-executor tests exercise Thumb-to-ARM interworking, an ARM PLT tail branch through the local import stub, instruction-width range enforcement, and stopping before an escaped store. Other tests cover in-bounds dynamic terminators, `DT_TEXTREL`/`DF_TEXTREL`, overlapping loads, clean initial registration state, PLT permissions and size, defined-symbol PLT rejection, and mismatch reporting across fresh Unicorn instances. Executable function and PLT ranges must lie within file-backed executable bytes; writable object validation may include zero-filled memory. This is a narrow ELF mapper, not an operating-system dynamic loader: it does not apply RELRO, invoke constructors or initialization arrays, model native scheduling, or execute real imports. The probe itself is Python and emulates ARM32 instructions; no native binary build target or Honda runtime was introduced. This is isolated emulator execution of a private artifact-derived target routine, not execution on ARM hardware or in the target process; the public synthetic tests are `SYNTHETIC_MODEL_ONLY`.

## Honda integration boundary

Previously published project analysis describes the reviewed Honda receiver path as preserving stock Type110 while skipping unsupported Type111 in the examined SETUP path; that evidence does not establish a supported extension contract. See the [prior architecture decision](42b-type111-architecture-decision.md) and [receiver handoff preparation](CL-STAGEB-JMCS-CONNECTED-DELTA-preparation.md). The three candidate shapes remain:

- **Existing extension contract:** no authorized receiver-owned Type111 delegation API is established in the public evidence.
- **Additive native integration:** still unsupported without an authorized interface that defines the actual caller/callee ABI, response ownership and serialization order, session identity/generation, failure propagation, resource cleanup, and preservation of factory Type110.
- **Independent media receiver:** still requires a receiver-authorized session association and protected stream handoff, or its own supported authentication authority. A locally functioning receiver does not confer Honda delegation.

The principal unresolved dependency is a versioned Honda-authorized receiver/display integration contract covering Type111 authorization, protected stream ownership, session and generation binding, teardown and revocation, factory Type110 isolation, and display admission. Type110 remains factory-owned. No Honda, Android, firmware, APK, or display runtime was changed or contacted. `safeForHonda() == false` remains unchanged.

## External reference findings

The version-pinned MHI2Q source and the **MHI2Q-2026-11-04** release provide two cross-target design constraints:

- The MHI2Q source treats `/info` advertisement and the control SETUP response gate as distinct. Its source and author notes report that its target phone requires accepted `enabledFeatures`, multiple display descriptors, and a secondary identity distinct from the primary. This is MHI2Q/version-specific source research, not a Honda or universal iPhone contract.
- The November 4 release adds session-specific renderer readiness on reconnect to avoid presenting stale prior-session frames. Session-bound readiness is a useful general design requirement; its hooks, QNX lifecycle, and firmware assumptions remain target-specific.

Harman's MHI2 project reports a real Stream-111 navigation demonstration on its exact Škoda MU1440 target, with a separate auxiliary stream path and factory primary stream. This is evidence for that target only and supplies no Honda API.

References: [MHI2Q November 4 release](https://github.com/luka-dev/mib2q-carplay-rgi/releases/tag/MHI2Q-2026-11-04), [pinned MHI2Q source at `8c738816c2af225c4ddfc9740528f876c08b2bf6`](https://github.com/luka-dev/mib2q-carplay-rgi/tree/8c738816c2af225c4ddfc9740528f876c08b2bf6), [Harman MU1440 development status at `f4d4da979627c00c3ed617ac67853adb7f428839`](https://github.com/harman-f/mhi2_altscreen_carplay/blob/f4d4da979627c00c3ed617ac67853adb7f428839/docs/status/CURRENT_DEVELOPMENT_STATUS.md), [Harman receiver profile and stream ownership at the same revision](https://github.com/harman-f/mhi2_altscreen_carplay/blob/f4d4da979627c00c3ed617ac67853adb7f428839/docs/architecture/SYSTEM_OVERVIEW.md).

## Safety and next milestone

No Honda/ADB/root/device access, vehicle network, firmware/APK modification, process interception, runtime patching, Type111 advertisement, phone stream, frame injection, or deployment occurred. No Honda binary, raw capture, credential, private vehicle/session identifier, or native internal reference is included in this change.

Next, obtain Honda-authorized receiver and display-host contracts (or an authorized sample implementation) that define Type111 authorization, protected stream ownership, generation binding, teardown/revocation, factory Type110 isolation, and display warning/composition priority. Until then, Honda compatibility remains unproven.
