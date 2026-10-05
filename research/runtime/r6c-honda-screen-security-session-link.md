# R6C screen security and authenticated session

The factory Type110 path derives a screen key/IV from the AirPlay receiver-session's 16-byte master material plus `streamConnectionID`; `AirPlayReceiverSessionScreen_SetSecurityInfo` installs the per-screen AES-CTR state. The same screen object processes framed media and finalizes its security state at cleanup. This is a **direct AirPlay session → Type110 screen-security link** in `jmcs`; see the prior [hash-matched crypto trace](../carplay/honda-screen-crypto.md).

The source of that AirPlay master material from iAP2/MFi/pairing is not established by this trace. Thus MFi authentication and screen key derivation share the broader session lifecycle conceptually, but a specific exported authenticated context or direct chip-to-screen derivation is **not proven**. Type111 derivation and concurrent Type110/111 security remain `UNKNOWN`. No key values or authentication material are retained here.
