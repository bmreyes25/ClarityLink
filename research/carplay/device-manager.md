# CarPlay device-manager trace

## Confirmed call chain

```text
mc_ScreenStreamStart @ 0xBDC06
  -> mc_dev_attach("CarPlay Screen", stream-associated context)
  -> devmgr_dev_attach(manager, name, context) @ 0x82858
  -> devmgr_dev_alloc @ 0x825F0
  -> internal dev_attach @ 0x81FF4
```

The public wrapper obtains the manager through a global pointer. The manager attach routine validates state/context, allocates a manager device handle, performs `dev_attach` while holding the manager lock, and updates manager linkage/reference state on success. `devmgr_dev_detach` is present at `0x82D28`.

`dev_attach` (`0x81FF4`) obtains the device key from the secure-pointer wrapper, walks the manager's linked entries beginning at manager offset `+0x08`, and invokes the first operation in each entry's interface with the registration entry and device key. It retains a matching/best entry and passes it to `dev_attach_to_app` (`0x81E64`). Thus the lookup is **callback/comparator based**, not demonstrated as a direct string-key hash lookup. Static evidence in this slice does not reveal which comparator returns the winning match for `"CarPlay Screen"`.

## Registry resolution

| Question | Result |
|---|---|
| Registry/manager object | MediaCore device-manager global; exact named C type unresolved |
| Lookup function | Internal `dev_attach` (`0x81FF4`); linked-entry iteration and comparator call are confirmed |
| Key supplied by CarPlay | Exact string `"CarPlay Screen"` |
| Match rule | Registered-entry comparator callbacks are invoked; winning comparator/entry for this key is unknown |
| Registration API/table | Not resolved |
| Matched registration/callback | Unknown |

Targeted symbol search found candidate media-device helpers and callbacks, including `media_dev_attach` and `media_dev_attach_cb`, but no evidence ties either to this exact registration. They are deliberately not treated as the match.

## Targeted registration table

| Device ID | Registration function | Ops table | Attach callback | Binary/object |
|---|---|---|---|---|
| `CarPlay Screen` | Unknown | Unknown | Unknown | local `jmcs` ELF |

The next static slice should decode `dev_attach` (`0x81FF4`) and its registry population/registration callers, then follow the unique match only. Do not broaden into unrelated media-device inventory.
