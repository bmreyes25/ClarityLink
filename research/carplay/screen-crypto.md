# Honda screen crypto

Step 38 refines the Type-110 derivation contract from the local identity-verified `jmcs` ELF.

`AirPlayReceiverSessionSetup` reads nonzero `streamConnectionID` as uint64 and calls `AirPlay_DeriveAESKeySHA512ForScreen` (`0x288d18`) with the 16-byte receiver-session master material, length 16, ID, and key/IV output pointers. The helper constructs two ASCII salts using `%s%llu`: `AirPlayStreamKey` + unsigned decimal ID and `AirPlayStreamIV` + unsigned decimal ID. It separately computes SHA-512 over each salt followed by the master material; the first 16 digest bytes become the screen key and IV. Setup installs these through `AirPlayReceiverSessionScreen_SetSecurityInfo`, then zeroes its temporary outputs.

The setter initializes AES-CTR in screen object `+0xc8`; replacing existing security finalizes the previous context. The screen stream uses an independent persistent CTR state and decrypts protected message bodies in place. Honda uses this path for Type110 only. Type111 reuse is MHI2 prior-art, not Honda-confirmed.

Offline implementation: `src/claritylink-negotiation/screen_kdf.py`, with synthetic 16-byte inputs and fixed expected output vectors. No real or derived vehicle keys are stored. Read `honda-screen-crypto.md` for byte-wise CTR state and the `jmcs` evidence chain.
