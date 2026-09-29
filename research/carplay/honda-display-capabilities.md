# Honda display capabilities — Step 30

Step 32 confirms that the exact dictionary returned by `AirPlayCopyServerInfo` is the object serialized for the `/info` response. Consequently the locally constructed `displays` array is phone-facing in static code flow. A mutable insertion window exists from the return at `0x28a156` to serializer call `0x28a19c` in `_requestProcessInfo`; executable hook safety remains unvalidated.

Step 31 additionally finds `AirPlayCopyServerInfo` absent from dynsym and no consumers among the 45 mapped shared libraries. The local array/dictionary are mutable, but no phone-facing serializer or mutation boundary is known.

AirPlayReceiverSessionPlatformCopyProperty (0x28d328) handles displays by creating a mutable CFArray, calling AirPlayReceiverSessionScreen_CopyDisplaysInfo (0x287ae0) once, and appending its returned main-display dictionary. AirPlayCopyServerInfo (0x282cd4) requests that property and inserts the returned array under displays in its mutable result dictionary. This confirms local descriptor construction and insertion; phone-facing delivery is still unknown.

The main descriptor's evidenced fields from the prior focused disassembly are edid, features, maxFPS, widthPhysical, heightPhysical, widthPixels, heightPixels, and uuid. Numeric fields are inserted with numeric CF setters; precise runtime values and complete semantic typing are not established here. uuid is inserted via numeric setter and must not be assumed to be a UUID string. features is a masked numeric value; bit meanings remain unknown. edid source/encoding and descriptor-to-wire semantics remain unverified.

| Field | Honda evidence | Type/value | Phone-facing |
|---|---|---|---|
| edid | Main descriptor dictionary | CF object/value details unresolved | Unknown |
| features | Numeric setter; source g_screen_features, mask logic in builder | Integer; bits unresolved | Unknown |
| maxFPS | Main descriptor dictionary | Numeric; exact value/source unresolved | Unknown |
| widthPhysical, heightPhysical | Main descriptor dictionary | Numeric; physical units/value unresolved | Unknown |
| widthPixels, heightPixels | Main descriptor dictionary | Numeric; exact values unresolved | Unknown |
| uuid | Main descriptor dictionary; numeric setter | Numeric representation; semantic UUID form unresolved | Unknown |

The returned displays array is CFMutableArray (constructed with CFArrayCreateMutable), and the server-info dictionary is mutable during construction. This establishes structural possibility of appending another local dictionary, not protocol acceptance or safe interposition.

See honda-display-descriptor.md, honda-server-info.md, and honda-display-capability-send-path.md.
