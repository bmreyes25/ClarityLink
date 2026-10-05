# R6H1 provisioning preflight

**Decision: `R6H1_PROVISIONING_BLOCKED`.** There is no verified CPC200-CCPA connected to this Mac. Therefore model/revision match, ownership, USB data path, power stability, tool-device compatibility, and vendor backup creation cannot be confirmed. No provisioning command, firmware write, or authentication traffic was attempted.

ECC review checklist (hardware-dependent items remain unverified):

| Check | Finding | Gate |
|---|---|---|
| Device match / model / revision | No CPC200-CCPA label or VID/PID visible; no device attached for examination | BLOCKED |
| Tool provenance | Public `f-io/LIVI` v9.2.0 release pinned; macOS ARM provisioner SHA recorded in toolchain baseline | PASS for source provenance only |
| Revision support | Upstream firmware names supported chipset families; specific unit must pass provisioner's probe | BLOCKED |
| User ownership and intended lab use | No physical unit or purchase provenance presented | BLOCKED |
| Power and USB data path | Cannot validate without unit and known-good cable | BLOCKED |
| Stock firmware backup / rollback | Upstream docs say the provisioner backs up before writing and describes restoring i.MX6UL vendor firmware; actual backup and restore availability cannot be proven in absence of unit | NOT TESTED |
| Wrong-device risk | No physical target; never launch provisioner without an operator checking the selected device/model | BLOCKED |
| Failure/rollback | Do not write until actual probe passes, backup exists, and restore path is understood for that unit | BLOCKED |

When hardware arrives, run the exact pinned, signed/provenance-checked upstream provisioner in its documented probe/backup flow. Stop if model/revision is unsupported or unknown, no backup is created, restore instructions do not apply, power is unstable, or unexpected devices are selected. Preserve the vendor backup outside Git and record only size, SHA-256, and private storage location. Do not improvise a low-level flash or backup method.

No provisioning approval is granted by this report; the required current result is blocked because its prerequisites are physically untestable.
