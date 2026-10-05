# R6F authority acquisition specification

## Obtain exactly

One **Carlinkit CPC200-CCPA wireless CarPlay/Android Auto adapter**, preferably the i.MX6UL + RTL8822BS/RTL8822CS or IW416 revision explicitly accepted by the current [LIVI Link provisioner](https://github.com/f-io/LIVI/blob/main/LIVI-LINK.md). Do not substitute CPC200-CP2A/CP2, CPC200-CCPW, generic wireless CarPlay adapters, or an unverified clone. Ask the seller to confirm the model label and hardware revision and use a returnable listing. Purchase only from an authorized MFi finished-goods source; verify the seller/manufacturer against Apple's current MFi source process. A marketplace model string alone does not prove authenticity.

The **software dependency** is the public [LIVI project](https://github.com/f-io/LIVI) plus its [LIVI Link provisioner/firmware](https://github.com/f-io/LIVI/blob/main/LIVI-LINK.md), used on the Mac. LIVI Link is not a separate item with a known retail price. It reflashes a compatible dongle and exposes network MFi authentication; LIVI owns the Mac-side CarPlay stack. Its docs list supported firmware/chipset families; the provisioner must confirm a specific unit before writing firmware. Back up stock firmware and accept provisioning risk.

## Why this target qualifies

LIVI states that CarPlay needs an authentic MFi coprocessor and on Mac the LIVI Link route is required. LIVI Link states it offers network MFi authentication and Mac-side phone pairing. LIVI is open source and supports macOS. This gives ClarityLink a legitimate full receiver stack to adapt. The CPC200-CCPA is not itself the ClarityLink control-session API: its MFi endpoint only covers the authority/radio portion.

## Connection and expected interface

CPC200-CCPA plugs into the Mac over USB. Depending on firmware, LIVI Link uses USB networking or the dongle's Wi-Fi AP; its web UI is documented at `http://livi-link.local/` or `http://10.10.10.1/`. On macOS the dongle handles Bluetooth pairing while LIVI owns the native CarPlay stack. The expected ClarityLink provider is a narrow adapter under `auth_providers/` around a documented/public LIVI session boundary. It must hand one authenticated request/response control channel, generation, session identity, and close ownership to `AuthenticatedSessionHandoff`. **No such stable external API is currently documented.** R6G/R6H work must expose/adapt the LIVI session internals; do not pretend the Link web UI or MFi signing endpoint is a control-session handoff.

## Cost and availability

A current retailer listing observed 2026-10-05 advertised CPC200-CCPA at approximately **USD $65** (sale/listing price; availability fluctuates and one listing showed a notification option). Another regional listing showed **AUD $94.95**. Budget USD **$65–$100 plus tax/shipping** as a planning estimate, and confirm stock, return policy, source authorization, exact revision and MFi provenance at purchase. LIVI source/provisioner is public; no separate licensed service fee is documented.

## What else is required

- A Mac with USB-A or a compatible USB-C data adapter/hub and a USB data cable capable of stable power/data.
- A real iPhone and a known-good wired/wireless setup; do not capture personal identifiers or phone content.
- Stock firmware backup, current LIVI Link provisioning tool, and LIVI macOS build dependencies.
- GPL-3.0 dependency/license review before code reuse/distribution.
- ClarityLink adapter work to surface the authenticated `/info` request/response channel; acquisition alone does not complete R6F integration.
- Verify the exact CPC200 revision is accepted by the provisioner before writing.

## First test after acquisition

1. Photograph/model-confirm the CPC200-CCPA label and preserve provenance privately.
2. Connect only to the Mac; read VID/PID and provisioner compatibility without sending authentication commands.
3. Back up stock firmware, then provision LIVI Link only after compatibility and source/licensing checks.
4. Verify the LIVI Link network endpoint is local/private and its MFi hardware test reports genuine hardware; redact all identities.
5. Run the upstream LIVI real-iPhone path before ClarityLink integration, then adapt the actual authenticated control channel into a single ClarityLink handoff.
6. First ClarityLink gate is one continuous session reaching real `/info`; no replay/synthetic result counts.

## Limits

The public docs do not prove the provenance of a retail unit, identify every compatible PCB revision, publish a stable ClarityLink-friendly control API, guarantee Type111 support, or guarantee stock availability. Confirm these with the seller/project before purchase. If the source cannot verify authorized genuine stock or provisioner compatibility, do not purchase/use that unit; request a verified LIVI Link compatible unit instead.
