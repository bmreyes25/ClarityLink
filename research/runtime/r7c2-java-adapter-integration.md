# R7C2 Java adapter integration

The API17 test app executes production Java `PrimaryDisplayHost`, `DisplayDiscovery`, `SecondaryDisplayHost`, `AndroidAudioAdapter`, `InputBridge`, `AndroidUsbTransport`, `ProcessLifecycleAdapter`, and the production fail-closed iAP2/authentication/media contracts. It observes a synthetic second display, constructs and shows a Presentation, receives its Surface, opens AudioTrack, writes bounded synthetic PCM, pauses/resumes/flushes/closes (including double close), exercises input allowlist and generation rejection, enumerates the empty emulator USB manager, checks unavailable production auth/iAP2/CarPlay media defaults, and executes Java loopback sockets. Process lifecycle start/activate/stop is checked.

The test APK compiles against API17 with no AndroidX or later public API dependency. Synthetic receiver setup/media is enabled only by the explicit LAB test argument; production authentication is rejected first in every lifecycle cycle.

Limitations: loopback coverage is `java.net.Socket`, not execution of the native POSIX `AndroidSocketAdapter` through an Android socket JNI entrypoint. Android USB manager/no-device state is real, while permission-denied callbacks are not delivered by a real device. AudioTrack may report unavailable on a headless emulator; when open succeeds, lifecycle and write are checked. Arbitrary injected constructor/write/input-registration exceptions and stop races are not all exercised. No Honda audio, control mapping, or USB ownership is implied.

ECC review found no guessed steering key mapping, production authentication fallback, or Honda mixer route. Exceptions are logged/returned as explicit failures in exercised paths; un-injected framework fault branches remain listed in the fault matrix.
