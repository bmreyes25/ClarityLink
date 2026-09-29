# CarPlay media ownership graph

```text
ScreenSession
  -> ScreenStream
  -> mc_ScreenStreamStart
  -> mc_dev_attach("CarPlay Screen", stream-associated context)  CONFIRMED
  -> devmgr_dev_attach -> devmgr_dev_alloc -> dev_attach           CONFIRMED
  -> registry list, slot-0 ranking callback                         CONFIRMED generic mechanism
  -> selected registration for this key                              UNKNOWN
  -> selected slot-4 attach callback                                 UNKNOWN for this key
  -> concrete device/sink                                             UNKNOWN
  -> process_data +0x14                                               UNKNOWN for this instance
  -> H.264 / decoder                                                  UNKNOWN
  -> Surface                                                         UNKNOWN
```

The generic manager has a per-attach allocation record and stores the selected entry in it after successful attach. The manager pointer is reached globally. Neither fact proves independent concrete device, sink, decoder, or Surface instances. The second argument at the callsite is stream-associated, but its identity and handling by the concrete callback are not known.

| Multiplicity question | Verdict |
|---|---|
| Can call `mc_dev_attach` twice | Structurally callable; duplicate-key behavior unknown |
| Two device instances | Unknown |
| Two sink instances | Unknown |
| Two decoder instances | Unknown |
| Two Surfaces | Unknown |
| Unique attach context per stream | Unknown |
| Display-B media chain | Plausible as a conceptual graph only; unsupported by concrete ownership evidence |

No Display-B implementation should be based on this graph yet.
