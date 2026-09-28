# CarPlay media ownership graph

```text
ScreenSession
  -> ScreenStream
  -> mc_ScreenStreamStart
  -> mc_dev_attach("CarPlay Screen", stream-associated context)
  -> MediaCore device manager
  -> matching registration / attach callback       UNKNOWN
  -> concrete mc_stream_sink                       UNKNOWN
  -> process_data +0x14                             UNKNOWN for this instance
  -> H.264 / decoder                                UNKNOWN
  -> Surface                                        UNKNOWN
```

Confirmed lower-level interface facts: the generic sink interface has `ops`/`priv`, and slot +0x14 is `process_data`; the screen callback pushes data through that interface. The `mc_dev_attach` call is made for each observed `mc_ScreenStreamStart` invocation, but there is no evidence yet that two screen starts can coexist or yield independent device instances.

| Multiplicity question | Evidence-based verdict |
|---|---|
| Call `mc_dev_attach` twice | Structurally callable more than once; whether the manager accepts duplicate names/contexts is unknown |
| Two device instances | Unknown |
| Two sinks | Unknown |
| Two decoders | Unknown |
| Two Surfaces | Unknown |
| Unique device private/context per attach | Unknown; call receives a stream-associated context, but exact type/identity semantics are unresolved |
| Display-B media chain | Plausible as a shape only; unsupported by concrete registration/ownership evidence |

No Display-B implementation should be based on this graph yet.
