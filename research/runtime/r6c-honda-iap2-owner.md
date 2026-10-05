# R6C iAP2 ownership

**Preserved-build software owner: `jmcs` (`HONDA_STATIC_CONFIRMED`).** Its own symbol table contains `ios_iap2_*`, `iap2_core_attach`, `iap2_acc_auth_*`, `mc_iap2_attach`, and `mc_carplay_screen_iap2_attached`. Source-path strings identify `dev/ios/iap2`, `protocols/iap/iap2/features/iap2_acc_auth.c`, and `mediacore/drv/ios/iap2/carplay/mc_carplay_app.c`. These are compiled into `jmcs`, not unresolved imports from a separable iAP2 library.

The USB side is also present in the executable: `jiap_usb_host_mode_transport_*`, `process_udev_dev_usb_device`, `j_udev_authorize_device`, `g_usb_host`, and `g_usb_dev`. `jmcs` links `libudev.so`. This supports in-process USB/iAP2 ownership but does not identify the specific runtime USB file descriptor, kernel interface, or exact attach thread.

The observed conceptual chain is USB host transport → iAP2 physical/logical device → iAP2 accessory authentication and identification → `mc_carplay_*_iap2_attached`. The exact object passed from authenticated iAP2 to AirPlay control-session creation has not been proven. No transferable iAP2 session handle or external IPC was found in this pass. Thus the desirable `HondaIap2Transport` handoff is `EVIDENCE_REQUIRED`.
