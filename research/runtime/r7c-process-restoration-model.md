# R7C process and restoration model

The intended lifecycle is temporary `start → ready → active → disconnect → restore → stop`; no boot script, init.rc edit, preload, framework hook, binary replacement, or HondaHack dependency is introduced. Verification covers only ClarityLink-owned receiver/session, listener, surfaces, audio/input, USB/iAP2/authentication, decoder, and generation resources.

Conceptual replacement model: `STOCK_IDLE → CLARITYLINK_STARTING → CLARITYLINK_READY → CARPLAY_CONNECTING → CARPLAY_ACTIVE_PRIMARY → CARPLAY_ACTIVE_DUAL → DISCONNECTING → RESTORING → STOPPED`, with FAULTED edges from each stage. This does not kill or replace jmcs. Target testing must prove temporary start/stop without persistent changes and stock behavior restoration. Android lifecycle execution and repeated-cycle verification remain pending.
