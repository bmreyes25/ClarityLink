# Honda `/info` capabilities

**HONDA CONFIRMED:** `/info` dispatch reaches `_requestProcessInfo`, calls `AirPlayCopyServerInfo`, then sends the returned dictionary through the binary-plist response path. The display property is a CFArray containing one main-display dictionary. Known fields: `edid`, `features`, `maxFPS`, `widthPhysical`, `heightPhysical`, `widthPixels`, `heightPixels`, `uuid`; numeric UUID representation and feature-bit meanings are unresolved. See Step 32 and `honda-server-info.md`. The xcertplay field-by-field Type111 comparison is in [Step 43A](honda-info-type111-differential.md).

`DISPLAY ARRAY: YES` (the property is array-shaped). `SECOND DISPLAY STRUCTURALLY REPRESENTABLE: PARTIAL/UNKNOWN`: generic CF arrays can hold multiple items, but the recovered Honda builder selects `ScreenCopyMain()` once and emits one descriptor. Honda support/phone acceptance is unproven. ViewArea-like fields are not recovered. Do not add modern `altScreen` tokens without evidence.
