# 43S2 native Type111 SETUP transaction core

**Classification:** `LAB_EXECUTABLE_CONFIRMED` for the compiled ARM helper executing in the standalone Unicorn harness; `LAB_HOST_RUNTIME_CONFIRMED` for the same C transaction core linked to host callbacks and real loopback sockets. No result is Honda runtime evidence.

## Shape and ownership

`native_setup_txn.c` is compiled to ARMv7 Thumb by `build_thumb_shim.py` and linked into the same ELF32 object as `thumb_setup_shim.S`. The shim calls the compiled `project_prepare` and `project_finish` wrappers. They convert a fixed 32-bit test wire context into `ClSetupCall`, then call `cl_setup_prepare` / `cl_setup_finish`. The Unicorn harness executes the resulting machine code in one emulated address space; its hooks model only external service operations and the opaque stock serializer boundary.

The Type111 branch uses a process-wide, nonblocking service gate. A simultaneous/nested Type111 mutation receives `BUSY`, leaves the original response untouched, and proceeds to the stock serializer exactly once. It does not rely on Honda reentrancy. Independent host transactions use independent call/transaction storage. Service callbacks must be synchronous, non-throwing, thread-safe, and failure-atomic: a callback reporting failure retains no newly acquired ownership. The gate is released after commit or rollback.

The transaction object is 44 bytes and contains scalar tokens only: magic/state, gate token, generation, stream ID halves, port, original response count, and ownership flags. A compile-time assertion fixes its size. The 56-byte shim context records the native finish result for offline diagnostics. `ClSetupCall` pointers are borrowed only for the synchronous prepare/finish call. No request, response, status, session, socket, worker, or callback pointer is retained in `ClPreparedTxn`. The response addition is limited to `{type: 111, dataPort: assigned_port}`. Type110 entries remain untouched. Any unknown/unsupported/malformed Type111 request leaves the stock response unchanged.

## Completion rule

The shim invokes the modeled Honda serializer at one call site and never retries it. Project commit requires all of: prepared result, exact status pointer equal to original caller `SP + 0x50`, serializer `r0 == 0xc8`, and `*statusOut == 0`. Other outcomes restore the appended synthetic response and roll back the exact generation/listener. Cleanup callback errors are recorded as an internal finish result in the harness context, while stock serializer `r0` is still returned unchanged. As in the 43R contract, these conditions model the locally observed serializer predicate; they do not prove Honda accepts Type111.

## Concurrency and failure boundary

Host tests exercise nested calls, concurrent sessions, same-process contention, repeated IDs, supersession, and malformed request sweeps. Same-session or overlapping Type111 project mutation is serialized by the gate; a losing call is stock-only. The native core has no mutable static transaction state. Host integration compiles the C core as a shared library and crosses its service boundary into the existing real listener implementation. ASan/UBSan and TSan runs pass on the exercised host paths.

Expected project errors are ordinary results and are handled before the serializer: malformed input, unavailable gate, generation/listener preparation failure, invalid assigned port, serializer failure, commit failure, and stale/overlapping completion. The code cannot safely recover from arbitrary invalid non-null pointers, unmapped-memory faults, invalid instructions, or stack corruption. No signal-handler recovery is claimed. Callback implementations must honor failure atomicity; the synthetic service layer tests it, but a Honda runtime bridge has not been implemented or validated.

## Honda bridge boundary

The ARM harness uses clean-room fixed-width request/response structs. It does not call CoreFoundation or create/mutate Honda-owned CF objects. Preserved-ELF symbol/import evidence for CFArray/CFDictionary operations is static capability evidence only. Object ownership, retain/release requirements, response lifetime, and exact mutation ABI at the Honda serializer seam remain a separate runtime-bridge prerequisite. Do not map this synthetic struct directly onto an opaque Honda object.

The real-listener integration validates socket-before-advertise ordering and immediate loopback connection. `HONDA_INTERFACE_POLICY` remains unresolved. The accepted-socket security/framing decision remains `HONDA_UNKNOWN`; unknown input must be closed and its exact generation retired without invoking AES or ChaCha parsing.

## Reproduction and limits

Run `PYTHON=.venv/bin/python tools/run_tests.sh`. The compiled image is generated in memory/temp storage; no ARM binary, patch bytes, or install payload is produced. Unicorn is an instruction-level ARM/AAPCS test, not Android Bionic or Honda emulation. Host sockets establish host behavior only. The Honda target, its serializer, Type111 acceptance/security, and target interface reachability were not exercised.
