# `mc_stream_link` static trace

Binary: exact local `extracted/system-vendor/system/bin/jmcs` at the Step 14 analysis checkout. Function VA `0x8da00` (Thumb entry `0x8da01`), symbol size `0x58c`; DWARF source is `mediacore/core/mc_stream.c`.

## Contract and dataflow

DWARF names formal arguments `src` and `sink`. `mc_stream_link(src, sink)` returns a `result_t`. It checks for null/already-linked endpoints, then writes the relationship at `src + 0x0c = sink` and `sink + 0x08 = src`. It obtains endpoint operation tables and invokes their `init_instance` entries (offset +0x08); further linked setup includes message allocation/handling and failure cleanup. The link fields are accessed at `src+0x0c` and `sink+0x08`; note the latter lies beyond the 8-byte `mc_stream_sink` interface prefix, so the handle points into a larger/extended endpoint representation or the debug type describes only its prefix. `mc_stream_unlink` is a separate lifecycle path.

The `mc_stream_sink_ifc` declaration is 28 bytes: `init_instance` +0, `cleanup` +4, `enable` +8, `disable` +0xc, `alloc_buf` +0x10, `process_data` +0x14, `handle_msg` +0x18. The function receives the sink interface through that endpoint operation table; `mc_stream_link` itself does not choose an implementation or allocate the passed sink.

## Direct callers

Static direct-call scan finds:

| Caller | Classification | Evidence |
|---|---|---|
| `add_sink_stream_pair` (`0x4c318`) | PBS media-pipeline helper; CarPlay identity not established | direct call at `0x4c5d8`; the helper obtains a source from an existing stream and accepts a sink argument |
| `create_pipeline` (`0x4c8cc`) | PBS generic pipeline construction; CarPlay identity not established | direct call at `0x4ccb6` |
| `create_pipeline_nommf` (`0x4d5fc`) | PBS alternate generic pipeline construction; CarPlay identity not established | direct call at `0x4d638` |

`add_sink_stream_pair` obtains a source with `mc_stream_get_mmf_src` and receives a sink pointer as an argument, then invokes `mc_stream_link`. This explains the generic plumbing but does not identify the factory or type of the sink for CarPlay's `ScreenStream` callback.

No direct caller from the Honda `mc_ScreenStreamProcessData` / CarPlay screen setup functions appears in this direct-call set. The construction may be reached through another operation-table route, but no such CarPlay-to-PBS edge is established in this evidence. Thus these callers cannot be labeled active CarPlay construction.
