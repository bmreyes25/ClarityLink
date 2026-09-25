# Live CarPlay receiver topology, September 25

**Method:** parked car, Wi-Fi ADB. The first unprivileged `/proc/<jmcs>` reads were denied. A later narrowly scoped `su -c` read of the already running process's `maps`, `fd`, `status`, task names, and `/proc/net` was saved under `../captures/20260925T150706Z-root-proc-read/`. No process was attached, signaled, reconfigured, or replaced; no file was written on the vehicle. Raw paths and network addresses remain in the local capture because they may identify the phone/session.

## Observed path and confidence

```mermaid
flowchart LR
  phone[iPhone / USB accessory] --> usb[USB and /dev/jdev handles]
  usb --> jmcs[jmcs native receiver]
  phone --> ip[Two established IPv6 TCP flows]
  ip --> jmcs
  jmcs --> proxy[libcarplay_proxy.so mapped]
  jmcs --> binder[/dev/binder]
  jmcs --> alsa[/dev/snd/pcmC0D1p]
  binder --> cp[CarPlayApService]
  cp --> nav[NavigationApService binding]
  cp --> ext[ExternalDisplayApService binding]
  jmcs --> center[CarPlay center Surface]
  center --> hack[Honda Hack casting path]
  hack --> hdmi[HDMI display 1 / cluster region]
```

The diagram combines **observed process handles/bindings** with the separately inspected static and pixel paths. An arrow into a service means a Binder client relationship, not proof that maneuver data traversed it. Neither established TCP flow has been classified as a specific CarPlay control or video channel; payload capture and protocol validation would be needed.

The normalized [live service binding graph](../captures/20260925T150706Z-service-graph.json) records the relevant `dumpsys activity services` relationships without transient Binder addresses. It shows `CarPlayApService` among the clients of both `NavigationApService` and `ExternalDisplayApService`, and Honda Hack among the clients of `AvApService`. Those are live IPC edges, not evidence of Apple Maps route-field delivery.

| Link | Direct evidence | Interpretation limit |
| --- | --- | --- |
| iAP2/USB | `jmcs` threads include `J_IAP2_SESSION_`, `J_IAP2_SEND`, `iap2_dev_worker`, `jiap_usb_host_m`; open `/dev/jdev` and USB bus handles | Confirms live accessory machinery. `/dev/jdev` role is consistent with its static string in `jmcs`, but handles alone do not show Identification bytes. |
| IP transport | `jmcs` owns a listener and two established IPv6 TCP sockets to one peer on a link-local interface, plus UDP sockets | Confirms live socket transport; no stream identity or content can be assigned from `/proc/net` alone. |
| Native/Android bridge | `libcarplay_proxy.so`, `libstagefright_omx.so`, `/dev/binder`, NVIDIA graphics libraries are mapped; `CarPlayApService` has clients including CarPlay UI and external display | Confirms these components are loaded/bound, not a second video stream. |
| Navigation/external service | Live service graph shows `CarPlayApService` bound as a client of `NavigationApService` and `ExternalDisplayApService`; `ExternalDisplayOutService` and factory navigation service are running | A service binding is a potential integration seam. It is **not** a decoded Apple Maps turn, and the factory TBT setters remain excluded because they can emit B-CAN. |
| Audio | `jmcs` threads include `AirPlayAudioRec` and `AirPlayAudioMai`; it has an ALSA playback handle. `dumpsys audio` showed `AvApService` owning Android focus in both casting states; user heard voice in both | Establishes working audio during tested casting. The dumps are snapshots and do not map every audio sample to a named stream. |
| Video/display | One named center CarPlay Surface in SurfaceFlinger, Android HDMI display 1, actual paired screenshots, and physical Maps/Music mirroring photos | Establishes existing center-to-cluster casting. No independent iPhone cluster map appeared. |

The casting-off and casting-on SurfaceFlinger snapshots each show the same three non-dim **unnamed** 800×480 layers on stack 1 (z 61000, 181000, 181005). The HDMI pixels changed from compass to mirrored Maps without a new named layer appearing. This is consistent with Honda Hack updating an existing external-display view/surface; SurfaceFlinger alone cannot name the producer. `dumpsys audio` was byte-identical across the two snapshots, with `AvApService` holding focus on stream 12. The user's audible-voice observation is stronger evidence for actual navigation audio preservation than this focus snapshot.

## What remains unresolved

The saved kernel config has `CONFIG_USB_MON` unset, so built-in USB tracing is not a path to raw Identification on this unit. The current process topology supports a better offline twin, but does not establish whether the iPhone was offered Route Guidance or a second display. The copied `jmcs` code's one-main-screen registration and singleton proxy are stronger static evidence about the current receiver path; a byte-level protocol observation or reconstructed serializer is still needed before implementing an R15-style extension.

The September 25 decoder test independently showed two NVIDIA AVC instances outputting 28 frames each at 800×480 over about two seconds. That removes the old claim that the hardware is inherently limited to one decoder, under the tested fixture. It does not establish coexistence with the factory CarPlay decoder or a receiver ABI that can deliver a second stream.
