# R7E6 watchdog fault matrix

| Case | Host-native result | API17 x86 result |
|---|---|---|
| `--version` normal return | Pass (focused suite) | Not run |
| `--self-test` normal return | Pass (focused suite) | Not run |
| Child busy loop timeout | Pass | Not run |
| Child blocked sleep timeout | Pass | Not run |
| Parent timeout | Pass | Not run |
| Child crash mapping | Pass | Not run |
| Inherited ignored `SIGCHLD` | Pass | Not run |
| Fork failure | Pass | Not run |
| Waitpid error, exact-child recovery | Pass | Not run |
| Repeated host child lifecycles | Pass | Not run |
| 100 API17 version/self-test pairs | Not run | Not run |

The host suite result was 9 passed. Required emulator cases remain unproven because the local shared ADB server attached to the AVD; no guest command was sent. Do not report an incomplete or skipped runtime case as a pass.
