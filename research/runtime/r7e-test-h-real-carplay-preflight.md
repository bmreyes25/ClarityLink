# R7E Test H — real CarPlay/authentication preflight

**Plan state:** `AUTHORITY_REQUIRED` / `BLOCKED_BY_EVIDENCE` / `NOT_AUTHORIZED`  
**Risk:** Tier 4. No execution plan or command is approved.

Real CarPlay work remains blocked until all of the following are established independently:

- lawful genuine MFi authority, including allowed use and hardware/service owner;
- supported USB/iAP2 ownership and a complete authenticated receiver session owner;
- real iPhone `/info` handling and accepted real SETUP;
- production Type110 media security;
- production Type111 security and framing;
- safe Type110 center-display behavior and separately safe Type111 secondary-display behavior;
- ownership and preservation of Honda audio/controls/interrupts; and
- exact rollback, stop conditions, evidence capture, and separately authorized test plan.

R6D found no supported external authenticated-session handoff in reviewed factory surfaces. Do not assume stock `jmcs` authenticates and hands a session to ClarityLink. R6E found no lawful authority available in that milestone and did not reach a real iPhone session. CPC200/LIVI is not a mandatory R7E dependency for Tests A–G, but an actual lawful genuine authority will eventually be required for real-iPhone proof.

There are no proposed vehicle commands in this document. No ADB, USB, iAP2, MFi, `/dev/i2c-2`, `jmcs`, or real iPhone action is permitted by this plan. **Readiness:** `AUTHORITY_REQUIRED`; not authorizable from current evidence.
