# R5Y — Type110 preservation oracle

`capture_primary` records the exact primary object identity, descriptor identity, synthetic session ID, lifecycle marker, parent teardown owner, and canonical serialized **primary-only** response. `primary_preserved` compares these after optional child setup, failure, media and teardown. The response's first descriptor must remain the same object. This is stronger than equal field values inside the model, but remains `MODEL_ONLY`.

| Scenario | Expected oracle and child result |
|---|---|
| Secondary disabled | Primary unchanged; no child resources |
| Secondary succeeds | Primary unchanged; separate child generation |
| Setup validation or response creation fails | Original response; primary unchanged; zero child resources |
| Listener/security/decoder/display setup fails | Partial child cleaned; original response; primary unchanged |
| Setup commit fails | Candidate discarded; original response; primary unchanged |
| First/midstream, decoder or display failure | Child cleaned; primary unchanged and usable |
| Recoverable synthetic teardown error | All built-in mock resources closed; primary state still unchanged |

Tests exercise each branch and a 100-generation cycle. No test observes Honda center video, audio, control, or a real response body. A successful oracle cannot establish on-car Type110 preservation.
