# Honda SETUP Type 111 rejection — Step 30

Step 32 targeted the SETUP response for the modern `FeatureKey`, `altScreen`, `viewAreas`, and `enabledFeatures` markers. None occurs as a literal in this `jmcs` ELF, and no such string-token response array is evidenced in the recovered SETUP construction. This is not evidence that modern prior-art tokens are universally required; it means Honda support cannot be assumed. Type 111 remains rejected at `0x2861f6`; no implementation was made.

Step 31 status: no Type-111 implementation or live ABI validation was attempted. Existing static result stands: 111 reaches the invalid-type path near `0x2861f6`; exact external status, complete failure response state, and whether earlier entries' effects persist are unknown. The whole-array loop prevents claiming independent partial delegation without evidence. See [Step 31](../../step-reports/31-airplay-server-info-consumer.md).

AirPlayReceiverSessionSetup (0x2854e0) reads each streams[] element's integer type with CFDictionaryGetInt64 at 0x28590e. The recovered dispatch routes 100/101 to audio setup and 110 to AirPlayReceiverSessionScreen_Setup at 0x28609c. Type 111 follows the invalid-type path beginning at 0x2861f6 rather than screen setup.

\`\`\`text
streams[i].type (int64)
  -> AirPlayReceiverSessionSetup dispatch
  -> accepted cases 100 / 101 / 110
  -> default/invalid-type path for 111, starting 0x2861f6
\`\`\`

The local path rejects Type 111. The exact externally observable error/status mapping, full cleanup side effects, and whether other streams in the same request may already have caused side effects are not established by the current documented slice. Treat it as a rejected setup entry, not as a proven HTTP status code.

**Narrow future interception candidate:** the per-entry type dispatch inside AirPlayReceiverSessionSetup, immediately before accepted-type branches/default path. A selective handler could conceptually divert only type 111 and preserve the stock path for 100/101/110. This is a static architecture candidate, not a validated hook ABI or safe live patch point. Wrapping the invalid branch is narrower but requires exact response/error ownership and per-stream loop semantics before implementation.

For Type 110, Honda creates a listener and appends a response entry containing type=110 and dynamic dataPort; _connectionHandleMessage serializes Setup's response as binary plist and sends it through the existing HTTP path. No request identifier or display UUID is proven copied into that response. Type 111 response fields, beyond a candidate analogous type/port model, remain unknown.
