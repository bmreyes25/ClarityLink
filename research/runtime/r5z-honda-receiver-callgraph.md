# R5Z Honda receiver call graph

All Honda edges below are `HONDA_STATIC` from the preserved ELF or the cited repo static traces. There is no Type111 Honda edge and no R5Z binary patch.

```text
incoming HTTP request
  → _connectionHandleMessage
      → CF property-list request parse
      → AirPlayReceiverSessionSetup
          → typed streams[] iteration
          → Type110 branch
              → AirPlayReceiverSessionScreen_Setup
              → AirPlay_DeriveAESKeySHA512ForScreen
              → AirPlayReceiverSessionScreen_SetSecurityInfo
              → screen listener construction
              → _AddResponseStream(type=110,dataPort)
          → Type111: unsupported/skip
      → _requestSendPlistResponse
          → CFPropertyListCreateData
          → HTTPMessageSetBody
      → HTTPConnectionSendResponse

screen accepted socket
  → _ScreenThread / 128-byte header and body read
  → AES_CTR_Update for Type110 body when enabled
  → ScreenStreamProcessData / ScreenStreamSetProperty
  → libcarplay_proxy callback table
  → mc_ScreenStreamProcessData / Honda media sink
  → decoder and actual display target: PARTIAL / UNKNOWN

tearDownStreams / AirPlayReceiverSessionTearDown
  → known Type110 screen teardown
session finalizer
  → stock screen/stream/security release
Type111 dispatch and cleanup: ABSENT in inspected Honda path
```

Function existence was rechecked against the ignored local ELF (SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`) with `nm`; no addresses are needed for this versioned document. Evidence: [Setup send path](../../step-reports/27-honda-setup-send-path.md), [Honda request](../carplay/honda-setup-request.md), [screen framing](../carplay/honda-screen-framing.md), [video binding](../carplay/video-stream-binding.md), [decoder path](../carplay/decoder-output-path.md), [delegate/finalizer](../carplay/honda-session-delegate-lifecycle.md).
