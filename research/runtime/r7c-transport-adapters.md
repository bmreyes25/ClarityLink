# R7C transport adapters

The native socket adapter accepts numeric IPv4 unicast remote and explicit local bind addresses, nonzero port/generation, and bounded timeout. It rejects wildcard addresses, uses nonblocking connect plus `poll`, limits reads/writes to 1 MiB, reports partial writes, timeouts, peer close, and errno, suppresses SIGPIPE on writes, and supports shutdown/close. Target address/interface selection remains configuration evidence. Loopback is for offline tests only.

R7B's 15-byte header is synthetic test framing, not CarPlay framing. Production `CarPlayMediaTransport` remains unavailable until Type110/Type111 framing and security evidence exists; production construction must not select the synthetic parser.
