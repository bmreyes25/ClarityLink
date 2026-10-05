# R6E authorized authentication authority selection

R6D merge base: `88fa1095796056cd9f3a70e50616e7081b797da1`. Mac lab inventory found no configured provider, authorized service endpoint, or identifiable genuine MFi hardware in the available USB inventory. Environment names showed no MFi/adapter configuration. This is an availability finding for this host, not a claim about hardware elsewhere. No authentication attempt occurred.

Apple describes a genuine authentication IC and MFi-SAP for CarPlay: [Apple Platform Security](https://support.apple.com/guide/security/verifying-accessories-sec70a4f377d/web). Candidate project facts below come from public project documentation and are not authorization for use.

| Candidate | Authority type | Hardware / service | Mac | iAP2 / MFi / AirPlay-control owner | Handoff / documented API | License / credentials | Authorization / availability | Effort / verdict |
|---|---|---|---|---|---|---|---|---|
| User-owned genuine MFi coprocessor | GENUINE_MFI_COPROCESSOR | physical IC and host bridge | bridge dependent | new host stack / IC / new host stack | no selected control-session API | owner entitlement; genuine IC | not established / absent | high / NOT_AVAILABLE |
| User-authorized licensed service | LICENSED_MFI_SERVICE | licensed endpoint | API dependent | new host stack / service / new host stack | no selected or documented endpoint | licensed access, no copied key | not established / absent | high / NOT_AVAILABLE |
| User-owned genuine adapter appliance | GENUINE_HARDWARE | physical appliance | model dependent | adapter / adapter IC / adapter or host relay | adapter-specific, not connected | device ownership and license review | not established / absent | medium-high / AUTHORIZED_NOT_CONNECTED only after proof; currently NOT_AVAILABLE |
| [OCBM/CPC200](https://github.com/lvalen91/ocbm) | GENUINE_HARDWARE if genuine unit | CPC200 with genuine IC | public macOS host description | adapter / adapter IC / RTSP relay | public relay protocol; ClarityLink handoff unwritten | Unlicense project; unit provenance required | absent here | medium-high / ADAPTER_FEASIBLE |
| [xcertplay](https://github.com/shilapi/xcertplay) | genuine chip or authorized remote service | CH341/I²C or lawful service | Android first | xcertplay / chip-service / xcertplay | public MFi service API; no Mac ClarityLink control handoff | GPL-3.0; credentials/service required | absent here | high / RESEARCH_REQUIRED |
| [LIVI](https://github.com/f-io/LIVI) | genuine IC through LIVI Link on Mac | LIVI Link | documented Mac support | LIVI / Link IC / LIVI | no ClarityLink control handoff established | GPL-3.0; genuine Link required | absent here | medium-high / ADAPTER_FEASIBLE |
| xcertplay-compatible genuine hardware path | GENUINE_HARDWARE | owned IC/bridge | port needed | host / IC / host | adapter required | ownership required | absent | high / NOT_AVAILABLE |
| LIVI-compatible genuine hardware path | GENUINE_HARDWARE | owned LIVI Link | documented | LIVI / Link / LIVI | adapter required | ownership required | absent | medium-high / NOT_AVAILABLE |
| PlayPort default recovered/shared identity | none acceptable | software identity | Mac | PlayPort | no valid lawful handoff | restricted recovered material | prohibited | REJECTED |
| PlayPort with separate genuine authority | licensed/hardware, if proven | genuine authority | Mac | PlayPort / external / PlayPort | new handoff needed | GPL-3.0; no shared identity | no authority here | high / RESEARCH_REQUIRED |

No candidate is `USABLE_NOW`. A signer alone is insufficient: the authorized stack must hand over a live authenticated control request/response channel, generation, and close ownership. The selected R6E authority is **none** pending documented ownership and a physical/service connection. R6E result: `R6E_AUTHORITY_NOT_AVAILABLE`.
