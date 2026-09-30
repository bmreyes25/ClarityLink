# Next jmcs load/stream seam options

Step 41G leaves the Honda `LD_PRELOAD` behavior **UNKNOWN**: static strings and data tables do not prove behavior, and no isolated ARM user-mode/guest lab is present offline. It is not an active deployment path. This note compares alternatives without implementing or deploying any of them.

| Candidate | What it changes/needs | Can it receive Type111 without jmcs? | Current evidence/risk | Decision |
|---|---|---|---|---|
| jmcs wrapper launcher | Boot service command must change; wrapper eventually execs jmcs | No, not by itself | Doesn't alter jmcs internal calls. If it sets preload, it inherits the same unknown linker behavior; if it substitutes jmcs, it replaces stock receiver | Do not pursue as a preload workaround |
| Init service wrapper | Persistent boot ramdisk service edit and wrapper binary | No proven route | Adds startup/rollback complexity and still needs a separate stream integration mechanism | Not preferred |
| Binder/service companion | Existing service process/API, no jmcs injection if independent | Unknown | Local Honda IPC exists, but no recovered session/SETUP/Type111 transfer contract | Investigate only if API audit finds a receiver handoff |
| ExternalDisplay companion | Existing Honda display host/service and a way to deliver decoded frames | No proven Type111 ownership | Project evidence identifies ExternalDisplay View as a likely render target, not a proven CarPlay stream receiver | **Best next offline seam study** |
| Pure offline Type111 model | No target process entry; host-only synthetic protocol fixtures | No live stream | Can refine known/unknown response semantics but cannot provide vehicle integration | Parallel research option after service API inventory |
| Network-side receiver/proxy | Separate endpoint plus discovery, session authentication, routing, and crypto ownership | Potentially, but not proven | CarPlay negotiation/stream security and endpoint routing remain unresolved | Defer; highest protocol complexity |

## Recommended bounded next task

Inventory archived `ExternalDisplay`, `CarPlayService`, and related JNI/native/Binder interfaces. Return the process that owns each API, who opens the video stream, whether session/security material can be passed through existing supported IPC, and whether the service can present into the instrument-cluster display while preserving stock center CarPlay. Do not implement, modify startup configuration, or activate Type111. If no supported receiver handoff exists, record that result and compare a separate network-side receiver against returning to jmcs entry only after its preload gate changes.

The `LD_PRELOAD` seam is **UNKNOWN**, not proven absent. The current init service still lacks `LD_PRELOAD`, so any later attempt through this path requires a boot-ramdisk change and separate approval/recovery planning.
