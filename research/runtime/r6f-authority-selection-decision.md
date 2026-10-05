# R6F authority selection decision

**PRIMARY_AUTHORITY_TARGET:** user-owned Carlinkit CPC200-CCPA, i.MX6UL-compatible hardware revision, provisioned with LIVI Link, with LIVI's macOS receiver runtime as the authenticated session/control implementation to adapt.

**BACKUP_AUTHORITY_TARGET:** none selected. OCBM/CPC200-CCPA is not a backup for ClarityLink `/info`/SETUP ownership because its documented box protocol does not hand the phone-facing control channel to the host.

**Classification:** combined LIVI + LIVI Link target is `CARPLAY_SESSION_OWNER` today; the intended integration must become a `CARPLAY_CONTROL_SESSION_PROVIDER` by handing its authenticated live control channel to `ReceiverSession`. CPC200-CCPA by itself is an MFi/radio endpoint only. The current public LIVI interface does not document that handoff, so this is **not yet a completed authority integration** and does not qualify for R6F-T0.

**Why it wins:** it is the only reviewed path combining publicly documented genuine-hardware use, Mac support, and source for the full receiver-side iAP2/activation/control layers. LIVI Link explicitly describes network MFi authentication and Mac pairing; LIVI documents CarPlay on macOS and requires genuine MFi hardware. That makes the missing layers implementable from an available lawful software stack instead of leaving a signer with an entirely absent protocol stack. OCBM's session is kept inside the adapter; xcertplay is Android-oriented and signer-focused; a bare chip and service have no selected Mac control API.

**Conditions before calling it authorized/usable:** obtain the unit from a verifiable authorized finished-goods source; retain purchase/provenance evidence outside Git; verify the precise SoC/radio/hardware revision is supported by the current LIVI Link provisioner; confirm legal/license compatibility for the planned GPL-3.0 source integration; do not use any recovered/shared identity or vendor-supplied private credential. Public retailer descriptions are not proof of Apple MFi certification or the specific unit's genuine coprocessor.

**Acquisition required:** yes. See [acquisition specification](r6f-authority-acquisition-specification.md). Until purchase, provisioning, provenance review, and a ClarityLink control handoff succeed, R6F remains below T0.
