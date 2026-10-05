# R6A custom receiver readiness

Highest continuously demonstrated integration tier: **T1 generated clear media** (R5Z regression). Highest R6 ladder: **R6-L1 integrated receiver core**. R6-L2 needs a *complete* host `/info` and authenticated Setup, which are absent. The immediate target remains R6-L7.

| Component | Status | Evidence / blocker |
|---|---|---|
| USB transport | UNKNOWN | Honda owner/interface unknown |
| iAP2 | UNKNOWN | Honda and Python host handoff unknown |
| MFi/auth | BLOCKED | no installed-hardware/host provider integrated |
| /info | PARTIAL | display structure implemented; identity/HID/audio incomplete |
| session | PARTIAL | host state machine; no authenticated iPhone session |
| Type110 Setup | HOST_CONFIRMED | synthetic bounded model |
| Type111 Setup | HOST_CONFIRMED | synthetic transaction; 43P real phone was PlayPort, not this code |
| Type110 response | HOST_CONFIRMED | synthetic plist, Honda static shape oracle |
| Type111 response | HOST_CONFIRMED | prior-art lab profile, no phone acceptance here |
| primary listener | HOST_CONFIRMED | loopback only |
| secondary listener | HOST_CONFIRMED | loopback only |
| Type110 security | PARTIAL | Honda static algorithm, no host session integration |
| Type111 security | PARTIAL | generated-key ChaCha AEAD works; lawful session key/real vector absent |
| Type110 framing | HOST_CONFIRMED | bounded Honda-derived parser on synthetic input |
| Type111 framing | PARTIAL | PlayPort host profile implemented; raw real vector absent |
| H264 config | PARTIAL | bounded AVCC + SPS/PPS extraction; real VideoConfig unknown |
| H264 decode | HOST_CONFIRMED | generated clear Annex-B via FFmpeg |
| audio | UNKNOWN | stock reuse/host route unknown |
| controls | UNKNOWN | stock reuse/host HID unknown |
| Display0 | UNKNOWN | exact target sink unknown |
| Display1 | PARTIAL | 800×480 service ownership known; frame admission unknown |
| teardown | HOST_CONFIRMED | independent secondary/full generation cleanup |
| reconnect | HOST_CONFIRMED | 100-cycle synthetic regression retained |
| host iPhone lab | BLOCKED | Python receiver lacks auth/transport/full /info |
| API17 | UNKNOWN | port plan only |
| ARMv7 | UNKNOWN | no native build |
| Honda lifecycle | UNKNOWN | init/watchdog contract absent |

Integration ladder: T0 synthetic Setup; T1 generated clear media; T2 captured sanitized Setup; T3 captured media fixture; T4 lawful host iPhone Setup; T5 encrypted Type111; T6 decoded real frame; T7 displayed real host window. T2 has a sanitized Setup fixture but is not a continuously successful end-to-end transaction on this receiver, so T1 remains the reported maximum. R6 levels L0 pivot, L1 core, L2 full host info+Setup, L3 real listener, L4 real framing, L5 real security, L6 real decode, L7 real host display, L8 complete host dual receiver, L9 API17/ARMv7 build, L10 Honda adapters, L11 separately authorized parked-car execution, L12 simultaneous in-car displays.
