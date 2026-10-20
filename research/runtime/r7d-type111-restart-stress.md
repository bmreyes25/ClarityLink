# R7D Type111 restart stress

**Result:** `PASS`, 100/100 Type111 setup/frame/clear/close/restart cycles on the owned API17 Dalvik emulator. The same receiver generation and Type110 stream remain active; each cycle verifies Type110 before and after Type111 restart, clears the secondary Surface, closes/recreates only Type111, checks its owner counts, and asserts race-controller idle. 200 Type110 continuity frames passed.

The first attempt exposed a latched secondary setup cancellation flag after completed teardown. `ReceiverGeneration::close_stream(Type111)` now clears that flag under its mutex after releasing the secondary stream, allowing a later setup without changing Type110.

Evidence: [`/tmp/claritylink-r7d-type111-restart-final.log`](/tmp/claritylink-r7d-type111-restart-final.log) and [`/tmp/claritylink-r7d-type111-restart-final-runtime.log`](/tmp/claritylink-r7d-type111-restart-final-runtime.log). This is emulator-only synthetic evidence.
