# R6H1 CPC200 / LIVI Link toolchain baseline

## Decision

The selected target remains one genuine, user-owned **Carlinkit CPC200-CCPA** with a hardware/chipset revision that the pinned LIVI Link provisioner positively recognizes. The unit is absent from this Mac's USB inventory, so compatibility and provenance are `NOT_TESTED`. No device was provisioned and no auth request was sent.

## Mac baseline (read-only)

- Host OS reports macOS `27.2`, Apple Silicon `arm64`.
- Local tools: Node.js `v24.18.0`; pnpm `11.19.0`.
- `rustc` and `cargo` are not installed. No LIVI or LIVI Link executable was found in the standard app/bin locations searched.
- The R6H tree pins LIVI `f-io/LIVI` commit `dcb78854c59ba621f4d327910dc275da386496b4` for its isolated delegate patch. The public LIVI `v9.2.0` release is commit `a9562234429fc9d19d9f9804b6b288f9d435a922` (2026-10-03). They differ by four commits; retain the R6H patch pin and review/rebase it against the release only as a separate, explicit source change before hardware use.

## Provisioner and device support

- Public repo: [f-io/LIVI](https://github.com/f-io/LIVI), GPL-3.0-or-later; exact release pin `v9.2.0` / `a9562234429fc9d19d9f9804b6b288f9d435a922`.
- LIVI Link tool: `livi-link-provision-macos-arm64` from that release; SHA-256 `1bcdc730b9d8e740885cc958c998acf391b30f47e96e248f46ece50f9c3bf8ab`. It was not downloaded or run.
- Firmware assets documented at the pinned release include i.MX6UL + IW416, i.MX6UL + RTL8822BS, i.MX6UL + RTL8822CS, Allwinner V821B + AIC8800D80, and Axera AX520 + AIC8800D80. For CPC200-CCPA, prefer the explicitly identified i.MX6UL family, but let the provisioner's compatibility probe identify the actual connected unit before any write. Product name alone does not establish the SoC, Wi-Fi module, genuine MFi hardware, or revision support.
- LIVI Link documentation supports macOS and says the provisioner probes required firmware and saves a vendor backup before writing. For i.MX6UL devices it documents restoring vendor firmware with the same provisioner. This is an upstream-documented rollback path, not a guarantee that a particular unit can be restored; verify backup creation and restore choice before proceeding.
- Source-build notes in current LIVI docs require Node.js 24.x/corepack+pnpm, Rust stable >=1.88, and GStreamer.framework on macOS for the native video addon. The prebuilt LIVI app and provisioner release artifacts do not require a local Rust build merely to inspect their published checksums.

## User purchase/ownership gate

No CPC200-CCPA ownership/provenance was verified in this run. Before connecting a purchased unit, verify privately that its label says CPC200-CCPA, record seller/source and revision for the user's lab notes, and use an authorized genuine MFi finished-goods source with a return path. Never commit serials, receipt details, photos, private firmware backup, or personal identifiers. Ask the seller to identify the exact CCPA hardware revision and Wi-Fi module; do not substitute CP2A/CP2, CCPW, or an unverified clone.

## Sources and retrieval

Reviewed 2026-10-05:

- [LIVI Link support, provisioning, backup, and restore instructions](https://github.com/f-io/LIVI/blob/main/LIVI-LINK.md)
- [LIVI v9.2.0 release assets and hashes](https://github.com/f-io/LIVI/releases/tag/v9.2.0)
- [LIVI source/build and platform requirements](https://github.com/f-io/LIVI/tree/a9562234429fc9d19d9f9804b6b288f9d435a922)

No third-party binary was downloaded, no install script was run, no firmware was read or written, and no MFi secret or phone data was accessed.
