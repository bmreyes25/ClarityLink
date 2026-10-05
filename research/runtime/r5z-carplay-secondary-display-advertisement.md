# R5Z secondary display advertisement

43P's PlayPort laboratory session requested and received Type111 after a dual-display `/info` profile, with `altScreen`, `viewAreas`, and an `initialURL` present in that profile. Geometry was synthetic and the profile's individual causal fields were not isolated. Type111 preceded Type110 in the canonical trace. [43P](../lab/current-ios-type111-observation.md).

R5Z `SecondaryDisplayCapability` emits a minimal fixture with two display entries, an `altScreen` flag, and synthetic 800×480 / 30 fps secondary geometry. It is intentionally **not** a complete `/info` CarPlay payload and cannot by itself cause iPhone negotiation. The stock Honda `/info` handler and one-main-screen advertisement are `HONDA_STATIC`; Honda secondary advertisement fields are `HONDA_UNKNOWN`. Public xcertplay's [AirPlayInfoPlist](https://github.com/shilapi/xcertplay/blob/master/shared/src/main/java/com/shilapi/xcertplay/airplay/AirPlayInfoPlist.kt) is `EXTERNAL_PRIOR_ART`, not copied into R5Z.

Unknown fields include accepted display UUID/EDID, physical dimensions, view area, feature bits, URL values, rotation and security-generation influence. Each needs an isolated lawful lab comparison or Honda descendant artifact before compatibility claims.
