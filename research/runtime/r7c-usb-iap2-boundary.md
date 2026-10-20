# R7C USB and iAP2 boundary

Android public USB host APIs are documented from API12; API17 can enumerate devices, request permission, open a device, and perform control transfers. `AndroidUsbTransport` checks permission, generation, transfer size, and connection ownership. Generic support establishes neither Honda device ownership nor CarPlay accessory authorization. No copied Honda descriptor is used to claim or impersonate an accessory.

`Iap2Transport` and `Iap2Session` are separate interfaces. Default transport is unavailable; no iAP2 packet implementation or identity material is added. USB ownership and iAP2 readiness remain evidence-gated.
