# Honda hook point audit — Step 40

**Evidence:** exact local ELF, SHA-256 cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232; offline objdump/DWARF. Thumb function VAs are reported with bit 0 clear; a callable Thumb pointer has bit 0 set.

| Function / point | Static VA | ISA | Evidence and ABI | Ownership / decision |
|---|---:|---|---|---|
| AirPlayReceiverSessionSetup | 0x2854e0 | Thumb | DWARF prototype OSStatus(me, inRequestParams, outResponseParams); r0/r1/r2. Caller _connectionHandleMessage at 0x28af72 passes session, request dict, and sp+0x54 response slot. | Caller later sends and releases successful response. Entry is not selected; one BL call-site wrapper after stock is narrower. |
| _connectionHandleMessage | 0x28a30c | Thumb | Broad HTTP/AirPlay request dispatcher; Setup call at 0x28af72, /info is dispatched through _requestProcessInfo. | Too broad as one entry hook; a call-site wrapper is narrower. Full callback ownership/thread behavior unknown. |
| _requestSendPlistResponse | 0x289f60 | Thumb | Binary plist serializer/response sender; Setup and /info callers pass response objects. | Not selected: generic response path affects unrelated responses. It serializes synchronously in known callers. |
| _requestProcessInfo | 0x28a018 | Thumb | Calls AirPlayCopyServerInfo at 0x28a158; return in r0 is stored and passed to serializer at 0x28a19c; released at 0x28a1da. | Info capability mutation is required for the intended architecture. Candidate is the specific AirPlayCopyServerInfo call-site, not the handler entry. |
| AirPlayCopyServerInfo | 0x282cd4 | Thumb | DWARF signature: (session, properties array, MAC pointer, OSStatus *outErr) -> CFLDictionaryRef. Call-site args are r0-r3; result in r0. | Returns constructed serverInfo dictionary; caller passes it onward then releases it. Narrow candidate for info augmentation. Native CF mutation/replace ownership needs adapter validation. |
| AirPlayReceiverSessionScreen_CopyDisplaysInfo | 0x287ae0 | Thumb | Builds the main-screen descriptor; caller/property path places it in the displays array. | Not selected: it only constructs Honda's primary descriptor; intercepting whole serverInfo return is clearer. |
| AirPlayReceiverSessionScreen_Setup | 0x287d5c | Thumb | DWARF OSStatus(inSession, inStreamDesc, inSessionID) in r0-r2. | Internal Type110 screen setup; not needed for additive phone-facing capability/Setup response. Type111 stock does not reach it. |
| AirPlayReceiverSessionScreen_StartSession | 0x2883a8 | Thumb | DWARF OSStatus(inSession, inScreenStreamOptions) in r0-r1. Starts stock screen stream after accepted connection. | Not a project lifecycle target; no reason to intercept Honda Type110. |
| AirPlayReceiverSessionScreen_ProcessFrames | 0x287d8c | Thumb | DWARF OSStatus(inSession, inNetSock, inTimeoutDataSecs) in r0-r2. | Media-data hook explicitly excluded; project receiver must own its own Type111 path. |
| AirPlayReceiverSessionStart | 0x286398 | Thumb | DWARF OSStatus(inSession, inInfo) in r0-r1. | Future project lifecycle candidate to activate only after stock succeeds; not part of the two response call-sites. |
| AirPlayReceiverSessionTearDown | 0x2852ec | Thumb | DWARF parameters: session r0, params dictionary r1, reason r2, done pointer r3. | Future cleanup candidate for project-owned generation; do not call Honda cleanup for project resources. |

## Minimum set

For the initial no-op smoke, one selected call-site can be wrapped with exact stock delegation. For future two-plane augmentation, the narrow semantic set is:
1. AirPlayCopyServerInfo call-site at 0x28a158 (advertisement),
2. AirPlayReceiverSessionSetup call-site at 0x28af72 (stock response then optional append),
3. session start and teardown coordination (0x286398, 0x2852ec) before persistent resources are enabled.

The two response call-sites are **HIGH CONFIDENCE** as the smallest relevant control-plane boundaries. Persistent-state lifecycle points are an additional project fail-closed policy, not proof Honda requires four machine hooks. No media hook is required or justified. A single _connectionHandleMessage hook is broader and risks unrelated messages; _requestSendPlistResponse is broader still.

The mc_dev_attach("CarPlay Screen") registry path remains fallback-only.
