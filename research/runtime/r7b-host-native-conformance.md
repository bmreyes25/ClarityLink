# R7B host/native conformance

`tests/fixtures/r7b/vectors.json` is the shared behavior vector and references
two checked-in base64-encoded H.264 assets (repository policy prohibits tracked
binary fixtures). The build script materializes the bytes under ignored
`build/r7b/fixtures/`. Both the Python R7A reference and native harness consume
the same red Type110 and blue Type111 media bytes. The Python
test drives the reference's `/info`, Setup, separate listeners, decoding,
display delivery, and teardown. The C++ test drives the corresponding
generation/info/setup/transport/decode/output/close sequence.

Conformance assertions are behavioral rather than bit-for-bit: accepted stream
types and IDs, two active streams, one decoded 32x24 frame per independent
output, distinct media, correct stream/generation/timestamp association, and
zero resources after close. Python PNG and native RGBA representations are
intentionally different. The native harness also checks both stream orderings,
single-stream operation, duplicate/stale identifiers, malformed and oversized
packets, secondary failure isolation, output loss, post-close rejection, and
100 teardown/reconnect cycles.

Observed native result:

```text
NATIVE_R7B_PASS dual_orderings=2 secondary_isolation=PASS decoded_per_sink=102 cycles=100 malformed=PASS production_security=FAIL_CLOSED resources=0
```

The 102 count is the total decoded frames per sink over two ordering examples
and 100 lifecycle cycles. The conformance pytest compares the native result to
the shared JSON fixture after exercising the Python implementation. This is
`HOST_NATIVE_CONFIRMED`, not iPhone or Honda evidence.

Failure values are intentionally category-level (`false`/specific setup event)
in C++ instead of matching Python exception strings. No semantic mismatch was
observed for the compared outcomes. Exact SETUP plist bytes and transport
listener framing remain owned by the Python reference and are not claimed as a
native wire-compatible parser.
