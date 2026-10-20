# R7D display recreation

Stress repeats Presentation Surface destruction/recreation and Presentation dismissal/recreation on the synthetic API17 secondary display. Each race requires Type111 to stop using the old Surface and Type110 to post afterward. The harness targets 25 cycles of each case and asserts race-controller idle after each transition.

**Status:** run pending. External display removal/re-add is only considered if the API17 overlay display reports stable supported behavior; unsupported removal is not reported as PASS.

## Result

`R7D_DISPLAY_RECREATION=PASS`: 25/25 secondary Surface destroy/recreate and 25/25 Presentation dismiss/recreate cycles passed. Type110 posted after each Type111 loss; race-controller idle was asserted after all 50 transitions. The synthetic overlay display remained present, so external display removal/re-add was not exercised.

Evidence: [`/tmp/claritylink-r7d-display-final-runtime.log`](/tmp/claritylink-r7d-display-final-runtime.log) and [`/tmp/claritylink-r7d-display-final.log`](/tmp/claritylink-r7d-display-final.log).
