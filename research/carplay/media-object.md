# CarPlay media object evidence

## Proven generic API objects

DWARF in the exact `jmcs` ELF identifies `mc_stream_src` as a 12-byte structure with members `type` (+0), `ops` (+4), and `priv` (+8). Its associated `mc_stream_buf` is 32 bytes: `buf` (+0), `buf_size` (+4), `data_size` (+8), `timestamp` (+16), `free` (+24), `arg` (+28).

The related `mc_stream_sink` is an 8-byte structure with `ops` (+0) and `priv` (+4). Its DWARF interface `mc_stream_sink_ifc` is 28 bytes and names `init_instance` (+0), `cleanup` (+4), `enable` (+8), `disable` (+12), `alloc_buf` (+16), `process_data` (+20), and `handle_msg` (+24). Thus `mc_stream_push_data`'s load of a method from the related sink interface at +0x14 is specifically its `process_data` interface entry. This is a semantic name from DWARF, not an inferred decoder name.

## Screen callback relationship

`mc_ScreenStreamProcessData` reaches `mc_stream_alloc_buf` then `mc_stream_push_data`. The latter passes the related sink and a buffer pointer to the sink `process_data` operation. The `mc_stream_buf` carries a data pointer, data size, and timestamp, but this call site does not separately pass timestamp or flags as scalar arguments.

## Concrete instance limitation

The exact sink instance assigned to the CarPlay stream, its constructor, and its `process_data` implementation are still unresolved. The ELF contains a named Android MediaCodec MMF backend, but no verified constructor/vtable assignment yet connects that backend to this CarPlay sink. Therefore the concrete media object type, owner, and decoder linkage remain unknown.
