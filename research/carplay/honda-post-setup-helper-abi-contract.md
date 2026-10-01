# Honda post-Setup helper ABI contract — Step 43L.1

**Classification: PARTIAL.** This is a static contract sketch for a future offline prototype, not implemented code or a loading method. The best structural candidate is between the return of `CFObjectSetProperty` and serializer argument staging (`0x28afb2`); it is not proven safe for callout.

At the candidate boundary:

| Value | Source | Use |
|---|---|---|
| HTTP connection | preserved `r4` | Not required for child preparation; preserve for continuation |
| Original HTTP message | preserved `r6` | Serializer's `r1`, staged by Honda after helper |
| Receiver session | reload `[r10+0xf4]` | Opaque session identity only; do not retain/own Honda object |
| Parsed Setup request dictionary | `[sp+0x1c]` | Read-only scan only |
| Honda response object | `[sp+0x54]` | Borrowed pointer; preserve exact identity and caller-owned +1 |
| Setup/body status slot | `[sp+0x50]` | Preserve contents; Honda serializer receives its address later |

The caller frame is 8-byte aligned at the candidate (`push {r4-r11,lr}` plus `sub sp,#0x2b4`, total 728 bytes). A helper must obey AAPCS32: preserve `r4-r11`, restore SP exactly, treat `r0-r3/r12/lr` and flags as caller-clobbered, and return normally. The status can be ignored only if helper failures are entirely project-local: rollback all project resources, do not mutate the Honda graph on failure, and continue Honda's original response path. A helper must not throw/unwind across the caller, transfer ownership of the stock response, replace its dictionary, alter request contents, or write after serializer entry.

For any serializer-success commit observer, distinguish the return convention: `_requestSendPlistResponse` returns `0xc8` on body-install success and `0x1f4` on helper error; `[sp+0x50]` receives `HTTPMessageSetBody`'s return (zero means success). Header-init/plist-creation failure writes a nonzero error result through the output pointer. Do not treat `r0==0` as success. A commit observer must check both the HTTP status and output result before activating the synthetic child.

This ABI is not `COMPLETE`: callback safety, thread/lock/reentrancy behavior, method of entering the helper, and cleanup subscription remain unknown. No callout is authorized or implemented.

## Step 43L.2 lifecycle update

The finalizer path contains an interface notification, `MC_DEV_CARPLAY_SESSION_DESTROYED`, but it is not a session-addressable project subscription. The global callback record is one 24-byte slot copied wholesale by `mc_carplay_iface_set_cbs`; the callback receives interface plus event, not the AirPlay session. The per-session delegate setter likewise copies the complete 44-byte Honda-owned table. Neither proves chaining or multiple consumers. Honda finalization is optional for the project; the offline generation guard now owns idempotence, supersession, and configurable lease expiry. The callout remains the sole JMCS integration blocker. See [43L.2 finalizer audit](../../step-reports/43l2-session-finalizer-extension-audit.md).
