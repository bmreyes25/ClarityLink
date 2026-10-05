# R6D authentication lifecycle and locking

`os_auth_cp_obtain` enters `jmutex_lock_d`, checks the global fd sentinel, fetches device path/address, opens and selects the I²C slave, then stores the fd globally. `os_auth_cp_release` closes the fd, resets the sentinel and calls `jmutex_unlock_d`. The AirPlay certificate/signature wrappers obtain and release around each operation. `auth_thread` also uses the `uwh_ipod_cp_*` family. This supports **SINGLE_OWNER within `jmcs`**, with serialized access through the shared mutex.

An independent ClarityLink process does not inherit this mutex. Whether the kernel device or authentication IC tolerates cross-process contention while stock `jmcs` is active is `UNKNOWN`. No concurrent live access is designed or authorized. Retry/delay logic exists in the I²C helper and the AirPlay signature poll, but the effective timeouts and reset behavior remain partially unresolved. Host model release clears generation state on both success and failure.
