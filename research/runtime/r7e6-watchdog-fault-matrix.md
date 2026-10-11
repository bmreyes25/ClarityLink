# R7E6 watchdog fault matrix

| Case | Host-native result | API17 x86 result |
|---|---|---|
| Production `--version` | Pass | Pass; five initial + 100 repeated |
| Production `--self-test` | Pass | Pass; initial + 100 repeated |
| Child busy-loop timeout | Pass | Status 124; exact child reaped |
| Child blocked-sleep timeout | Pass | Status 124; exact child reaped |
| Parent timeout | Pass | Status 125; exact child and parent absent |
| Child crash mapping | Pass | Status 126; exact child reaped |
| Inherited ignored `SIGCHLD` | Pass | Pass; exact child reaped |
| Fork failure | Pass | Status 127; no child reported |
| Waitpid error recovery | Pass | Status 127; exact child kill/reap recovery |
| Repeated lifecycle/resource check | Host repeat pass | 100/100 version/self-test pairs; final test reports zero modeled resources |
| Exact emulator ownership | N/A | Private ADB server only; no foreign ADB process on emulator port |
| Exact staging mode/hash | N/A | `0555`; exact size/hash/MD5 assertions passed |
| Cleanup and final absence | N/A | Exact path removal and absence passed; emulator/AVD cleanup passed |

The host watchdog suite had 9 passing tests. Full API17 x86 evidence is retained locally in ignored `build/r7e6/runs/api17-runtime-69ad6acbcd28.json`. The final runner reports no failure and 100/100 cycles. No Honda or physical Android target was contacted.
