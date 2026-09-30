# Step 42A — Type 110 security fields and Type 111 boundary

## Honda Type 110 (confirmed static analysis)

The Type 110 Setup branch reads a nonzero uint64 `streamConnectionID` and passes it with 16 bytes of receiver-session master material (at the recovered session offset) to Honda's screen derivation helper. It independently computes key and IV using SHA-512 over `salt || master material`; salts are `AirPlayStreamKey` plus the unsigned decimal ID and `AirPlayStreamIV` plus the unsigned decimal ID. The first 16 digest bytes become the 16-byte key/IV. Honda installs them into the screen object's AES-CTR context, opens an ephemeral listener, and responds with `type=110` and its assigned `dataPort`. Temporary key/IV and salt buffers are zeroed in the analyzed path. No key/IV is sent in the Setup response.

See [Honda security contract](type111-security-contract.md) and [KDF analysis](honda-screen-crypto.md). No actual session key or captured key material is included here.

## Type 111 compatibility matrix

| Question | Honda evidence | Prior-art evidence | Step 42A result |
|---|---|---|---|
| Same authenticated session | Honda's Setup is a receiver-session method; Honda's unsupported Type 111 branch does no Type 111 setup. | MHI2 extends the stock authenticated receiver session. | **UNKNOWN for Honda Type 111** |
| Reuse session master material | Type 110 uses session master material; no Type 111 derivation occurs in Honda. | MHI2 uses its session's master material for Type 111 derivation. | **UNKNOWN for Honda** |
| New `streamConnectionID` | Honda's Type 110 requires an ID; unsupported Type 111 path does not read it. | MHI2 reads Type 111's ID. | **UNKNOWN for Honda; prior-art candidate** |
| Separate key/IV and CTR state | Honda's screen setter replaces one Type 110 screen context; no secondary context exists. | MHI2 owns a separate Type 111 receive context. | **Required by ClarityLink design if separate stream is proven; Honda wire/KDF compatibility unknown** |
| Separate `dataPort` | Honda Type 110 creates one listener and returns its port. | MHI2 owns a private Type 111 listener and returns its port. | **Prior-art candidate; Honda Type 111 unimplemented** |
| Same ScreenStream framing | Honda's 128-byte framing evidence describes its known screen path, not a Type 111 path. | MHI2 uses a Type 111-specific receiver implementation. | **UNKNOWN for Honda** |
| Same H.264 extraction/decoder path | Honda Type 110 helper and current offline parser have recovered framing/conversion behavior. | Apple documents independent H.264 CarPlay streams; MHI2 demonstrates its own path. | **Codec family plausible; Honda Type 111 parser/decoder reuse UNKNOWN** |

Do not mark Type 111 authenticated, derive keys, choose an ID policy, emit a response, or persist secrets based on the MHI2 analogy. The standalone offline KDF tests use synthetic values only.

## Decision

```text
TYPE111 SECURITY MODEL: PARTIAL (Type 110 confirmed; Type 111 Honda path absent)
TYPE111 AUTH SESSION REUSE: UNKNOWN
TYPE111 MASTER MATERIAL REUSE: UNKNOWN
TYPE111 STREAM CONNECTION ID: UNKNOWN for Honda
TYPE111 DISTINCT KEY/IV: UNKNOWN for Honda; separate context is an isolation requirement of the proposed design
TYPE111 SCREENSTREAM REUSE: UNKNOWN
TYPE111 H264 PIPELINE REUSE: UNKNOWN
```
