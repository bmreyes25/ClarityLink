# Honda native load seam inventory

Offline search only. The archived `jmcs` imports `dlopen`/`dlsym`, but inspected call sites belong to generic dynamic-loader/SQLite support; no ClarityLink plugin lookup or known CarPlay extension registry was recovered. `libcarplay_proxy.so` is a linked/mapped CarPlay callback proxy, but no evidence shows it loads arbitrary modules or offers a plugin API.

| Candidate | Owner / trigger | Path control and persistence | Assessment |
|---|---|---|---|
| Existing `DT_NEEDED` dependency | jmcs startup | System binary dependency graph; changing it requires binary/dependency deployment | no extension seam proven |
| jmcs `dlopen` calls | jmcs generic loader paths | no relevant controlled library path or plugin name established | not a proven seam |
| libcarplay_proxy callback API | jmcs startup/callback registration | stock library interface; callback table is singleton and second registration is rejected | useful hook observation point, not a loader |
| Java `System.loadLibrary` / JNI | Android app process | no evidence the app runs in jmcs or loads native code there | no |
| `LD_PRELOAD` / wrapper | process startup | no init wrapper/environment entry found in reviewed material; persistent startup change likely | hypothetical, high deployment risk, not established |
| plugin/config directory, property, init service env | system startup | no matching registry/path/environment seam established in reviewed evidence | unknown/no positive candidate |

Deployment fields (persistent files, root, reboot, rollback, brick risk) cannot be responsibly assigned to a nonexistent proven seam. Any future deployment requires a separate bounded-write review. Best current answer: **NO SUITABLE LOAD SEAM PROVEN**. This does not negate conditional in-process self-location.
