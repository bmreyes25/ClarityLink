# Honda session finalizer registration — 43L.2

`AirPlayReceiverSessionSetDelegate` (`0x285040`, Thumb) copies exactly 11 32-bit words from its input to session offset `+0x14`; it is a whole-record overwrite. Its only direct caller found is `_AirPlayHandleSessionCreated` at `0xaf252`. That creator allocates Honda context and populates the per-session delegate record, including `_AirPlayHandleSessionFinalized` at slot `+0x0c` (stored Thumb pointer `0xae655`). The record is session-local and Honda-owned.

The finalized handler also emits an app interface event through global `g_carplay_cbs` at `0x355b6c`. DWARF declares the callback record as `mc_dev_carplay_iface_cbs_t`, size 24 bytes, with `event_cb` at offset zero. Event 2 is `MC_DEV_CARPLAY_SESSION_DESTROYED`. `mc_carplay_iface_set_cbs` copies 24 bytes into the existing callback record; this is replacement, not append/register. The event callback ABI is `(mc_dev_carplay_iface_t *, mc_dev_carplay_iface_event_t)`, without an AirPlay session argument.

No session-delegate add/remove/chain function, callback-list traversal, or previous-callback storage was found in the bounded static search. Honda has an event callback for its interface consumer, but not a proven multi-subscriber extension point suitable for project session cleanup.
