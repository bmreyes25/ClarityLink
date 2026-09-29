# Honda stream type request dispatch

The confirmed SETUP response path establishes the returned stock stream dictionary has `type=110` and dynamic `dataPort`, and is serialized phone-facing (Step 27). This does not establish how request stream types are parsed or routed.

The tracked Step 26–27 disassembly slices recover response construction and the `_connectionHandleMessage` call into Setup, but do not include a complete request-side parser/control-flow trace for the incoming `streams[].type`. No contextual evidence found in the tracked research identifies a Type-111 comparison, accepted-type switch, generic fallback, or error path. The user-provided `type=111` scenario remains a hypothesis.

```text
KEY: request key "type" is not recovered in Honda parser evidence
CONVERSION: unknown
SWITCH / COMPARISON: unknown
KNOWN VALUES: response-side 110 only
DEFAULT BEHAVIOR: unknown
HONDA TYPE DISPATCH: unknown
TYPE111 WOULD REACH GENERIC SETUP: unknown
```

Do not infer acceptance from `_AddResponseStream` or from the fact a response array can structurally hold multiple entries. Recover the parser from `_connectionHandleMessage`'s request dictionary and follow its stream loop/dispatch before designing Stage B.
