# Honda hook plan — offline design

| Candidate | Static role/status | Interposition assessment |
|---|---|---|
| `AirPlayReceiverSessionSetup` `0x2854e0` | internal Setup implementation; called at `0x28af72`; Thumb; local, not dynsym export | Direct internal call means ordinary symbol interposition is not established; existing plan favors caller call-site interception. |
| Setup response mutation caller `0x28af72` | Thumb BL to Setup, caller owns output pointer and passes response to serializer | Best structural stock-first boundary; prologue hook unnecessary if callsite hook is retained; mutation ABI must remain exact. |
| `AirPlayCopyServerInfo` `0x282cd4` / callsite `0x28a158` | `/info` builder; one main display; local symbol absent dynsym | Intercept callsite to returned dictionary, not dynamic symbol lookup. |
| SessionStart `0x286398` | lifecycle coordination candidate | observation/ownership only if persistent generation state becomes necessary. |
| SessionTearDown `0x2852ec` | cleanup candidate; Honda Type 110 cleanup | project-owned Type111 cleanup must be independent. |
| SetSecurityInfo `0x287d28` | Honda security setup | observe only; never extract/persist keys. |
| display capability builder | one-element array through `CopyDisplaysInfo` | exact phone boundary is `/info`; augment only with further Honda proof. |

ARM/Thumb bytes and indirect/local-binding details remain those in existing hook fingerprint/callsite reports; this milestone did not recensus full binary because host ELF tooling was unavailable. Unknown target => no operation. No inline patch implementation.

**Step 41B correction:** Honda `libdl.so` provides `dladdr`, but the relevant Honda receiver routines remain jmcs-local/non-dynsym and cannot be obtained via ordinary `dlsym`. `libcarplay_proxy.so`'s six `mc_carplay_proxy_*` functions are genuine dynsym exports and are useful as a pointer to locate the proxy module, not as a substitute for the Setup function. The setup callsite `0x28af72` is a direct Thumb BL, so LD_PRELOAD symbol interposition does not observe that internal call. The Info builder callsite `0x28a158` is likewise a direct Thumb BL. Small validated callsite hook favored; exact runtime shim and safe patching remain unready. `AirPlayReceiverSessionSetSecurityInfo` should not be made an interposition target without separate role proof; observe existing stock security setup only.
