# Screen media interface table

The recovered interface is `mc_stream_sink_ifc` (DWARF in `jmcs`, source path embedded as `mediacore/core/include/mc_drv_strm_if.h`), 28 bytes. Entries are function-pointer fields:

| Offset | DWARF member | Function for this CarPlay instance |
|---:|---|---|
| +0x00 | `init_instance` | unresolved |
| +0x04 | `cleanup` | unresolved |
| +0x08 | `enable` | unresolved |
| +0x0c | `disable` | unresolved |
| +0x10 | `alloc_buf` | unresolved concrete implementation |
| +0x14 | `process_data` | unresolved concrete implementation |
| +0x18 | `handle_msg` | unresolved |

`mc_stream_push_data` (`0x8ea18`) obtains the linked sink, reads its `ops` pointer, then calls entry +0x14 with `(sink, mc_stream_buf*)`. The function identity `process_data` is directly supported by the DWARF declaration and slot offset. This resolves the role of the indirect dispatch but not the target address for the active CarPlay stream.

The Android adapter and MediaCodec backend are separate named code. Merely finding their symbols in the ELF does not identify this table's active implementation. The current evidence does not prove the table address, constructor write, or any concrete CarPlay slot target.
