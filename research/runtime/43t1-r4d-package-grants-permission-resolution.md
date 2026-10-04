# 43T1-R4D — package grants and permission resolution

## Evidence set

Reviewed saved package manifests and `research/extracted/config/data/system/packages.xml` (API 17 snapshot), plus the HondaHack-copied `platform.xml` and AOSP API17 permission declarations. The package-manager dump is preserved static state, not a fresh query; effective runtime checks were not made.

| Permission / identity | Finding | Classification |
|---|---|---|
| `SYSTEM_ALERT_WINDOW` | AOSP API17 dangerous permission; packages.xml defines protection value 1. `ExternalDisplayOutService` manifest requests it. The shown grant item is in `android.uid.phone` shared-user permissions, not the separate `com.mitsubishielectric.ada.app.externaldisplay` package record (UID 10056). | DOCUMENTED_ANDROID / HONDA_STATIC; effective host grant UNKNOWN |
| `INTERNAL_SYSTEM_WINDOW` | AOSP API17 signature permission; packages.xml protection value 2. The shown grant item is in `android.uid.phone` shared-user permissions. Honda ExternalDisplay manifest requests it, but package record is standalone UID 10056 with no sharedUserId. No grant item is shown on that package record. | DOCUMENTED_ANDROID / HONDA_STATIC; effective host grant UNKNOWN |
| `android.permission.PRESENTATION` | No such permission definition/request was found in the reviewed artifacts; API17 `Presentation` itself is a framework API, not a permission named PRESENTATION. | HONDA_STATIC; UNKNOWN beyond reviewed set |
| `ACCESS_MAP` | Navigation requests `com.honda.displayaudio.navi.permission.ACCESS_MAP`. HondaHack's copied `platform.xml` maps it to `media_rw`; no owning package permission declaration/protection level or effective grant to an ordinary package was recovered. This is not evidence of display admission. | HONDA_STATIC; custom permission details/grant UNKNOWN |
| `VEHICLE_RW` | Several Honda packages request it. No `<permission>` definition was recovered in reviewed manifests or the package permission-definition section. Its protection/grant model is unknown. | HONDA_STATIC; UNKNOWN |
| Honda package identities | Preserved packages.xml lists ExternalDisplayOutService UID 10056, ExternalDisplay AP UID 10055, CarPlay UID 10040, CarPlay AP UID 10041, Navigation service UID 10067, and Honda Navigation UID 10090 as distinct package UIDs with no sharedUserId. Distinct signing identities also appear in package records; do not publish certificate material. | HONDA_STATIC |
| Third-party grants | HondaHack package UID 10091 has a package-level `SYSTEM_ALERT_WINDOW` item in this snapshot. It is a third-party grant precedent for that installed package only, not an ordinary-app Display 1 admission or signature entitlement. | HONDA_STATIC |

No relevant `privapp-permissions` XML or complete OEM signature policy was present in the reviewed set. Manifest request is not proof of grant. The preserved state provides no evidence that an arbitrary ClarityLink package receives Honda custom permissions, shares a Honda UID, or can use Honda signing keys. A normal app could request dangerous `SYSTEM_ALERT_WINDOW` in generic API17, subject to grant and OEM behavior; signature `INTERNAL_SYSTEM_WINDOW` cannot be assumed available to it. Public `Presentation` does not inherently require either permission in generic AOSP, but Honda admission remains unproven.

**Answer:** package grants strengthen privilege/signature uncertainty but do not prove the ordinary public Presentation route impossible. No Honda package/privilege route is considered available to ClarityLink. @ECC review verified every claim against package record vs shared-user grant scope.
