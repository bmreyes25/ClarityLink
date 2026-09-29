# Honda Identification / ReceiverInfo search

Available static evidence separates two code families: iAP2 Identification state/building symbols and `AirPlayReceiverSessionScreen_CopyDisplaysInfo`, a CarPlay/AirPlay display-info builder. Tracked captures do not contain raw iAP2 Identification bytes. The available generated disassembly does not establish a direct call from the display builder to an Identification serializer or from a phone-facing Identification/ReceiverInfo response to this builder.

The display builder's local output is one dictionary. Its parent, serializer, transport, and timing remain unknown. No phone-facing message containing `Displays`, `Screens`, `Modes`, or a recovered `CopyDisplaysInfo` result was proven in the inspected evidence. Do not equate iAP2 accessory Identification with the later AirPlay SETUP binary-plist response.

```text
CopyDisplaysInfo participates in Identification: UNKNOWN
CopyDisplaysInfo participates in ReceiverInfo/Info: UNKNOWN
Display capability protocol phase: UNKNOWN
Phone-facing serializer/send path: unresolved indirect boundary (caller not recovered)
```

Next useful offline task: recover indirect references/callback table initialization for `AirPlayReceiverSessionScreen_CopyDisplaysInfo`, then trace its output pointer to the enclosing call and serializer. Raw packet capture would be a later, separate evidence step; no vehicle action is part of Step 28.
