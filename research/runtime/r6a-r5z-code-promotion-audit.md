# R6A R5Z code promotion audit

R5Z source: `08a17ee520963720b5ed4ba5f286882c2a9c3edf`. R6 merged its full commit history atop R5D main. [Original R5Z report](../../step-reports/43t1-r5z-custom-jmcs-type111-receiver.md) retains experimental evidence status.

| Module | Classification | R6 action |
|---|---|---|
| `receiver.py`, `setup.py`, `listener.py` | production-direction host reference | maintain session/generation, transactional Setup and socket ownership; fix stale response and duplicate primary |
| `capabilities.py` | evidence hypothesis | replace minimal flag fixture with prior-art display structures; still incomplete /info |
| `security.py` | production-direction interface + evidence hypothesis | explicit profiles/provenance, fail closed for encrypted Type111 |
| `media.py` | host-only Type110 framing hypothesis | named profiles; unknown Type111 fails explicitly |
| `decoder.py` | host-only adapter | FFmpeg remains isolated; AVCC converter added |
| `display.py` | host-only adapter | PNG/memory; GUI still pending |
| `compat/honda/*` | static evidence stubs | remain explicit EVIDENCE_REQUIRED, never host mocks on target |
| `tools/r5z_receiver_lab.py`, R5Z fixtures/tests | synthetic test support | retain regression and provenance; future real-lab harness is separate |

No Python module is considered Honda deployable. The target language and adapter contract are decided in the [portability ADR](../adr/r6-receiver-language-and-portability.md).
