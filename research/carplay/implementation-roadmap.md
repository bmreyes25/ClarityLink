# ClarityLink implementation roadmap — Step 37

| Phase | Goal | Entry requirements | Success signal | Current status | Blocker |
|---:|---|---|---|---|---|
| 1. Finish media format | Reproduce Type110 ScreenStream config/video media bytes offline | Honda `jmcs` disassembly and exact callback chain | Synthetic stream gives converted parameter sets and timestamped Annex-B media buffer | **Substantially complete offline**; parser, CTR state, config, extractor, receiver core implemented and tested | callback zero-run byte normalization and timestamp units still need exact decoding |
| 2. Type111 Setup + security | Recover mixed `streams[]`, session security, Type111 request/response contract | Exact Setup and key derivation call paths | Field/ownership/error matrix is proven; offline request model passes synthetic mixed-stream cases | **Next phase, not started** | Type111 entry contract, key derivation integration, response/rollback behavior |
| 3. Complete offline receiver | Assemble framing, key model, message parser, decoder-ready data contract | Phase 1 plus Phase 2 security inputs | Synthetic Type111 envelope creates config/media/control events with continuous crypto | Partial Type110-compatible core only | No Type111 request/security model; no real AES provider/key derivation |
| 4. Live interposer engineering | Design isolated Setup interception and listener lifecycle | Phase 2 and 3 complete; primary preservation review | Offline ABI/lifecycle tests and safe rollback design | Not ready | Hook site safety, thread/reentrancy, delegation contract |
| 5. First parked Type111 TCP proof | Prove phone connects to dedicated listener while primary CarPlay remains healthy | Phase 4 reviewed and explicit live test plan | Type111 TCP accept; Type110 center path intact | Not ready; not authorized/executed here | No compatible request response/interposer |
| 6. Live decrypt / config / H264 | Prove real transport crypto and media framing | Phase 5 connection proof | Valid decrypted header, avcC-like config, H264 media buffer | Not ready | No live Type111 crypto proof or test |
| 7. Head-unit decoder | Feed received access units to a chosen decoder | Phase 6 valid media; decoder API decision | Decoded synthetic/live frame output | Not ready | Active Honda sink/decoder linkage and format handshake unknown |
| 8. ExternalDisplay / cluster output | Render secondary frames to safe cluster host | Phase 7 and supported surface/view lifecycle | Navigation image appears in approved cluster region; center unaffected | Existing renderer skeleton only | ExternalDisplay host acquisition and physical viewport |
| 9. Presentation control | Implement show/stop/ViewArea ownership as required | Transport and cluster output work | Phone selects/clears cluster UI predictably | Not ready | Honda/iPhone control contract unresolved |
| 10. Maps/Waze polish + failsafe | Validate providers and failure recovery | Phases 1–9 and stable primary preservation | Maps/Waze tests, recovery and fail-clear behavior | Not ready | All later-phase behavior |

Scope of this status is offline. No live Type111 test, vehicle access, or code hook was attempted.
