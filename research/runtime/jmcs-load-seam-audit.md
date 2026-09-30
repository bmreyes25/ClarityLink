# jmcs load-seam audit

| Candidate | In jmcs? | Existing stock mechanism? | Persistent change | Status / primary failure |
|---|---:|---|---|---|
| Existing plugin/dlopen registry | unknown | no CarPlay plugin registry found | none if one existed | NO proven seam; generic SQLite extension loader is not a Honda plugin seam |
| `libcarplay_proxy.so` | yes | stock dependency and callback ABI | replacement/substitution would replace stock binary | partial interface seam, no arbitrary load or safe replacement proof |
| `LD_PRELOAD` via init environment | yes, if startup env supplied | AOSP + Honda linker markers indicate technical support | init service/env config plus staged library | no Honda service definition/config source preserved |
| Native dependency shim | yes if loaded by DT_NEEDED | no optional controlled slot found | jmcs binary or dependency replacement | no legitimate existing slot |
| Wrapper executable | yes if init invokes it | no wrapper identified | init/service change and wrapper | unsupported by archived start config |
| Java/JNI load path | usually separate app process | CarPlay APK/service exists | app/package change would load in Java process | not evidence of loading into jmcs |

The archived `CarPlay.apk`/`CarPlayService.apk` are present, but no preserved decompilation or process evidence establishes that a Java `System.loadLibrary`/`JNI_OnLoad` path runs inside `jmcs`. A library loaded by those APK services would ordinarily belong to their app process, which does not solve the target-process requirement. Treat JNI entry as NO PROVEN PATH.

Scorecard conclusion: **LOAD SEAM PROVEN: NO**. **Persistent change required: likely YES**, but exact file/line cannot be named because the jmcs init service definition is missing from the archived extracted filesystem. The smallest architecture-conditioned future change would be one init service `setenv LD_PRELOAD <absolute audited library>` option with an immutable hash gate and file-level rollback, only after obtaining the actual service file and validating init parser support. It is not deployable as stated. Replacing jmcs or `libcarplay_proxy.so` is broader and riskier.
