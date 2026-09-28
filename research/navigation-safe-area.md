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

Obtain **one synchronized, read-only capture of the factory Navigation page** consisting of (1) the actual HDMI/display-1 frame for that state and (2) a perpendicular full-cluster photo with the complete lit panel/bezel visible. The car must be parked, Honda Hack casting off, and the OEM Navigation page active. The paired frame/photo should include a known panel boundary or calibration reference so a projective transform and the visible native page bounds can be measured independently of the cast layout. If the instrument cluster composes the page outside display 1, the frame will show that limitation; the smallest further evidence would then be a read-only native meter framebuffer/page-layout snapshot from the controller that owns the Navigation view. A cast-on image is not an acceptable substitute.

## ClarityLink scope update — 2026-09-28

The project now targets only an independent secondary CarPlay display inside the existing map region; it does not require replacing the full cluster UI or identifying unused panel specifications. The next proof is diagnostics-first: determine the head unit's display devices, candidate framebuffer and Honda destination path through parked, read-only ADB diagnostics. Existing saved evidence reports built-in and HDMI logical outputs at 800×480, which is not a measurement of the native Navigation rectangle. A photo is a validation step if diagnostics do not expose enough geometry. No new rectangle evidence was collected in the latest ADB check, which returned no connected device.
