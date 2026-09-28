# Factory Navigation safe-area evidence

**Verdict: UNKNOWN.** The selected copied code/configuration does not expose an OEM factory Navigation rectangle in a known cluster coordinate space. Task A's success criterion is met by identifying the smallest missing observation; no on-car read or display modification was performed.

## Candidate rectangles and coordinate spaces

| Candidate x, y, width, height | Coordinate space | Source / exact evidence | Type and confidence | Actual factory Navigation safe area? |
|---|---|---|---|---|
| `0, 0, 800, 480` | Android primary-display logical pixels | `extracted/system-vendor/system/vendor/media/mcs/j_config.xml:97–101` (`System/Display`: 800×480 px, 153×92 mm); `:165–172` (`ScreenProperties`: video 800×480, max 30 FPS, touch mode hifi). | **CONFIRMED** configured primary/center-display dimensions. This is a full display mode, not a cluster navigation inset. | No. |
| `0, 24, 584, 191` | Local coordinates inside Honda Hack's 584×215 meter layout | `research/simulator/working-backup/meter_civic.xml:2, 74–75`: root 584×215; cast container has 24 px top padding; ImageView fills its remaining area using `fitXY`. | **CONFIRMED** layout-local cast image size; **UNKNOWN** mapping to Android HDMI/cluster pixels. | No. It is the cast view, expressly not an OEM Navigation-page bound. |
| `x=?, y=?, width=?, height=?` | Factory Navigation page / cluster-native coordinates | No matching OEM rectangle/Region/viewport/crop constants in the bounded files below. | **UNKNOWN**. | This is the target. |

The Android screen and Honda Hack layout are different coordinate spaces. No parent-layout origin, scale, crop, rotation, or transform from the 584×215 view to the 800×480 display or the cluster's native panel was found. `fitXY` establishes how an image fills the local `ImageView`, not where that view lands in a cluster display. The Step 2 browser overlay is therefore a visual proxy only; its placement must not be reused as a factory safe-area measurement.

## Bounded component findings

- `Navigation.apk` contains only its manifest/resource table among the checked package entries; no Navigation-page XML layout is present. `Navigation.odex` exposes semantic `NavGuide`, `NavCurrent`, and `GuideDispDemand` interfaces and route-data fields such as road width/offset, but the targeted string check found no `Rect`, `Region`, `Surface`, `Display`, x/y bounds, or cluster navigation rectangle constants. Road geometry fields describe route data, not screen coordinates.
- `HondaNavigationLib.odex` defines the TBT Binder surface (`ITBTInformation`, `setGuideDispDemand`, `setNavCurrent`, `setNavGuide`). `NavigationLib.odex` exposes callbacks for those semantic objects. They establish data APIs, not a pixel viewport.
- `ExternalDisplayOutService.odex` has logical `screenId`/`topViewId`, navigation/TBT callback classes, and Android `Display`/`Surface` type references. The focused field/string scan produced no OEM navigation x/y/width/height rectangle. Its APK has no relevant `res/layout` or dimensions XML entry in the targeted package listing.
- `ExternalDisplayApService.odex` has generic display IDs and width/height terms, but no configured factory Navigation bounds. `ExternalDisplayLib.odex` contains meter content IDs (including a navigation shortcut-menu ID), packet-size and Binder method names; these are content/transport identifiers, not coordinates.
- `/system/bin/cluster` dispatches to `cluster_$1.sh`; `cluster_set.sh` writes a named value to `/sys/kernel/cluster/$1` and `cluster_get.sh` reads it. These wrappers do not name a rectangle or pixel buffer.
- `disp_com_meter` strings identify local meter/center message endpoints and I2C command traffic through `/dev/i2c-0`/`ioctl`. This is evidence of command/control transport, not proof that it transports CarPlay pixels or encodes an image rectangle.

## CONFIRMED / HIGH CONFIDENCE / INFERRED / UNKNOWN

- **CONFIRMED:** Android main/HDMI logical screens are 800×480 in the saved capture/configuration. The Honda Hack layout-local image area is 584×191 at `(0,24)` inside 584×215.
- **HIGH CONFIDENCE:** the listed Navigation APIs carry semantic guidance into Honda display services; they do not supply an exposed Android `Rect` for the instrument-cluster Navigation page in the examined code/data.
- **INFERRED:** the eventual factory arrow/text view may be laid out by the meter controller or another layer behind the `disp_com_meter` command boundary. The evidence does not identify its native renderer or coordinate transform.
- **UNKNOWN:** exact factory Navigation x/y/width/height, panel resolution/coordinate origin, safe-edge margins, pixel format, final scaling/rotation, and whether those bounds exist in the head-unit copy at all.

## Minimum missing observation

The required paired factory Navigation Display 1 frame and physical photo have been collected. They show that the Android frame does not contain all physical cluster indicators, but do not provide a calibrated transform into physical cluster coordinates. If precise physical bounds become necessary, the next observation should add a known scale/panel reference or an OEM-owned viewport coordinate source; no repeat of the same uncalibrated capture is currently useful. No raw framebuffer read is authorized by the available metadata.

## ClarityLink scope update — 2026-09-28

The project now targets only an independent secondary CarPlay display inside the existing map region; it does not require replacing the full cluster UI or identifying unused panel specifications. Read-only ADB diagnostics and paired display-1 captures are now available. The latest evidence is summarized below; the native Navigation rectangle remains unknown.

## Paired Display 1 evidence — 2026-09-28

Factory Navigation, HondaHack Advanced Meter, and HondaHack Screen Casting were each captured through `screencap -d 1` as valid 800×480 PNGs. In every SurfaceFlinger dump, Display 1 is the HDMI display on layer stack 1 and its active layer source and destination frames are full-frame `[0,0,800,480]`. No Android source crop or destination inset is exposed.

The factory frame's compass/grid and Menu match the physical cluster photo. The photo also shows speedometer, charge/power, range, and status indicators that do not appear in the Display 1 screenshot. Therefore Display 1 is an input/output canvas related to the visible Navigation content, not a complete capture of all instrument cluster UI. The evidence is consistent with additional cluster-side composition or masking, but does not prove the exact location, dimensions, transform, or whether it is a hardware mask versus another downstream renderer.

HondaHack Screen Casting produced a different Display 1 image (Instrument Cluster settings and Menu over a black remainder), and Advanced Meter also changed visible pixels. Static APK analysis now traces HondaHack's output to a normal View injected by Xposed into Honda's ExternalDisplay InterfaceWindow root. The named `MeterActivity` layer is on Display 0/layer stack 0; it is not the Display 1 output layer. HondaHack's layout-local cast rectangle `(0,24,584,191)` remains unproven as a physical cluster destination.

**Updated verdict: the Android Display 1 canvas is confirmed as 800×480; native factory Navigation destination rectangle remains UNKNOWN.** No physical safe-area dimensions are inferred from the photo.


## Live display diagnostics — 2026-09-28

Read-only ADB confirms the Android HDMI logical display is display 1, 800×480 at about 60 Hz, layer stack 1. SurfaceFlinger/HWC reports the active HDMI source and destination as the full 800×480 frame. This is the head-unit output surface; it does not expose the smaller native factory Navigation map rectangle.

Framebuffer sysfs exposes `fb1` on `tegradc.1`, with mode 800×480p-59, virtual size 800×960, stride 3200, and bits_per_pixel=0. Its alignment to Android display 1 is likely by matching indices but is not directly proven. The format/byte allocation is not safe to assume, so no /dev/graphics/fb1 read was performed. The installed screencap display-1 path was used to collect the required states.

HondaHack's rendering mechanism is now traced to its injected View and ExternalDisplay host, but the factory Navigation physical rectangle and scaling/crop remain unknown. No additional live capture is currently required to continue the protocol model.
