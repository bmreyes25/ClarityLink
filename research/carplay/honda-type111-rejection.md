# Honda Type-111 SETUP behavior — Step 38

Honda `AirPlayReceiverSessionSetup` (`0x2854e0`) reads `streams[]`, gets each `type` as an integer (`0x28590e`), and branches to supported 100/101 audio or 110 screen setup. Type 111 enters the default/unsupported log block (`0x2861f6`). That block only logs; it does not write the Setup status slot, remove prior responses, or mutate stream/session state. Control falls through to the common index increment (`0x286220`) and continues.

After iterating, Setup calls `AirPlayReceiverSessionPlatformControl`; its result becomes final status. If zero, the response dictionary is assigned to the output pointer (`0x286260`). The phone-facing caller serializes and sends only on Setup success. Consequently, 111 is non-fatal at the transaction level when all supported stream work and final PlatformControl succeed. `[111,110]` and `[110,111]` both allow Type110 setup; Type111 itself contributes no response entry. A stock Type110 response already appended remains in the response array.

No rollback follows unsupported 111. A separate error from a supported stream invokes the Setup error/teardown path and may roll back supported streams. No external HTTP status or phone acceptance is inferred from static control flow.

| Condition | Honda effect |
|---|---|
| Type111 only | skipped; final result depends on common PlatformControl; empty `streams` response on success |
| Mixed Type111 + valid entries | Type111 skipped; valid entries handled normally; valid responses survive absent another error |
| Type111 after Type110 | no cleanup/rollback of Type110 |
| Type111 before Type110 | no blocker to later Type110 |
| Other setup/control error | separate error path; may invoke `AirPlayReceiverSessionTearDown` |

This corrects earlier Step 30/37 descriptions that left transaction status unknown. Evidence remains static, with no vehicle or ADB work. See `honda-mixed-stream-setup.md` and `step-reports/38-type111-setup-security-contract.md`.
