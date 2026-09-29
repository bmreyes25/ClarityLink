# Interposer failure model (Step 39)

| Failure point | Host behavior |
|---|---|
| Stock Setup failure | Return stock status/response; allocate no project resource |
| malformed/duplicate Type111 | Return stock response; no generation |
| security provider | Return stock response; no listener |
| fake socket/bind/getsockname/listen | Return stock response; no published entry |
| response build/append | Close acquired fake listener and return stock response |
| publisher/serializer | Roll back all project resources and return stock response |
| stock SessionStart failure | Roll back prepared generation |
| accept/parser failure | Caller observes error; explicit generation teardown releases ownership |
| repeated teardown | No-op after first cleanup |

Failures are isolated to project resources. This model does not establish timing/ownership at the real Honda callback boundary.
