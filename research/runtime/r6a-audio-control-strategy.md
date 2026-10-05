# R6A audio and control strategy

| Function | Classification | Evidence / needed interface |
|---|---|---|
| CarPlay media audio | UNKNOWN | jmcs links Android media/OpenSLES; same-session routing and reusable sink unproven |
| Siri audio and microphone | UNKNOWN | input/output route and focus ownership untraced |
| phone calls | UNKNOWN | telephony focus/HFP relationship and mute contract untraced |
| touch | ADAPTER_REQUIRED | center/Display0 coordinates must map to CarPlay HID; exact Honda event source unknown |
| steering controls / Siri button | ADAPTER_REQUIRED | Honda control event source and HID command mapping unknown |
| home/back | ADAPTER_REQUIRED | stock dispatch behavior needs static tracing |
| center display interaction | CUSTOM_RECEIVER | Type110 must remain primary and coordinate with audio/control adapters |

Stock reuse is a hypothesis until ownership boundaries are established. Event injection and vehicle testing are outside R6A.
