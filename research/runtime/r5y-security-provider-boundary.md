# R5Y — mock security provider boundary

`MockSecurityProvider` creates a generation-owned `SecurityContext` with only `mock-security-N`, initialized/ready/destroyed booleans, and a symbolic `unwrap_symbol` transformation from `frame-N` to `clear-frame-N`. No key, IV, cipher, derivation, authentication, secure transport, or encrypted payload exists. This is `MODEL_ONLY`, `NOT_REAL_CARPLAY`, and `NOT_MFI`; the word “security” denotes lifecycle state only.

The context rejects use before ready, after destroy, or with a different generation. Destruction is idempotent and belongs to the child cleanup manager. Setup failure after context creation destroys it. Media failure destroys it without changing the primary snapshot. A new generation receives a distinct context object and label.

Replacing this mock would first require Honda-specific Type111 framing/security evidence, schema and stream identity correlation, lawful authentication material, ownership and teardown behavior, and independent security review. The modern 43P PlayPort branch and Honda Type110 crypto do not establish Honda Type111 security. None of those requirements is satisfied by R5Y.
