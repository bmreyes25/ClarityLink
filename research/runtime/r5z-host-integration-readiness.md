# R5Z host integration readiness

| Level | Result | Evidence |
|---|---|---|
| L0 architecture | PASS | Static map, call graph and explicit adapters |
| L1 Setup parsing/response | HOST PASS | Binary plist lab serialization; Honda Type111 schema unknown |
| L2 Type111 listener lifecycle | HOST PASS | Loopback, one connection, generation check, teardown |
| L3 media framing | LAB HYPOTHESIS PASS | Bounded Type110-family header parser; not established for real Type111 |
| L4 security provider integration | INTERFACE ONLY | Clear local fixtures; real encrypted Type111 fails closed |
| L5 H.264 decode | HOST PASS | Public FFmpeg, locally generated Annex-B fixture |
| L6 host secondary display | HOST PASS | PNG frame sink and teardown clear; no actual cluster |
| L7 real iPhone lab | NOT RUN | No MFi/authentication or real receiver negotiation |
| L8 Honda ABI compatibility design | PARTIAL | Type110 field adapter and static map; no CF/runtime bridge |
| L9 Honda Display1 adapter design | PARTIAL | Evidence gap/contract only; z-order and admission unknown |
| L10 vehicle deployment | OUT OF SCOPE | No car experiment authorized |

Highest fully completed level is **L2** under the ordered success ladder. L5/L6 host components pass with generated clear input, but they do not advance L3/L4 for real Type111. The CLI's `synthetic-client` mode exercises session → response → loopback socket → bounded framing → clear lab security → FFmpeg → host sink → teardown. `lab-receiver` accepts only one localhost connection from a lawful clear fixture; it is not an iPhone receiver. `captured-setup` parses sanitized JSON without authentication or live CarPlay.

The host test cannot prove stock-equivalent Type110. Its oracle compares modeled Type110 response state and port across Type111 success/failure. It cannot validate Honda's original listener, crypto, media, or finalizer. See [proof limits](r5z-jmcs-compatibility-map.md) and [R5Y boundaries](r5y-what-this-proves-and-does-not-prove.md).
