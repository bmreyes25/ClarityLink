# `CopyDisplaysInfo` indirect caller search — Step 29

## Result

The tracked checkout does not contain the `jmcs` ELF, relocation tables, DWARF DIEs for the function-pointer interface, or a complete disassembly image suitable for a pointer-storage search. It contains generated disassembly excerpts, symbol metadata, and string maps. Those artifacts identify `AirPlayReceiverSessionScreen_CopyDisplaysInfo` at VA `0x287ae1` / file offset `0x287ae0`, but expose no callback registration, stored function pointer, initializer, ops table, or indirect call site that can be tied to its signature.

| Requested item | Evidence-backed result |
|---|---|
| Function pointer storage | Unknown; no relocation/data image or xref index in tracked artifacts |
| Callback table / slot | Unknown |
| Initializer | Unknown |
| Interface type / neighboring slots | Unknown; no usable DWARF function-pointer type or table layout |
| Indirect callers | Unknown; no full instruction/reference corpus available for signature matching |
| Phone-facing caller | Not established |

The Step 28 result remains the local routine: it returns one dictionary built from one `ScreenCopyMain()` result. Absence of a visible direct caller in the saved disassembly is not proof that the routine is unreachable or unused indirectly.

## Search boundary and next evidence needed

The needed artifact is the exact `jmcs` ELF (or complete raw `.text`, `.data`, `.rodata`, relocations, and DWARF for the matching build). With that, search literal function-pointer relocations/address literals, data initializers and constructor writes, then trace candidate indirect calls and compare ARM EABI argument/return dataflow to the routine's signature. Do not infer an interface from the function name or neighboring symbols alone.

**Conclusion:** indirect caller unresolved; phone-facing capability path unresolved.
