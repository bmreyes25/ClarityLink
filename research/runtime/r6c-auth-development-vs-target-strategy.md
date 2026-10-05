# R6C development versus target authentication

**Final Honda target:** the preserved build uses an I²C-connected factory authentication device through code inside `jmcs`. Reuse without retaining `jmcs` receiver ownership remains **unproven**. No second in-car MFi device is part of the target design.

**Mac lab:** Honda's target I²C hardware and in-process `jmcs` state are not a Mac authentication service. Real-iPhone host development still needs an independently authorized genuine MFi device/service **and** a host control-session handoff, unless a different lawful lab substrate becomes available. Whether such infrastructure is already owned or accessible here is `UNKNOWN`.

These are separate gates. A future Mac lab success would not prove Honda adapter reuse; a future Honda auth API would not itself supply a Mac lab authority.
