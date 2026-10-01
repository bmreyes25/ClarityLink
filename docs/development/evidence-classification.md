# Evidence classification

Apply these labels to research, models, reports, and demo output:

| Label | Use |
|---|---|
| `HONDA_CONFIRMED` | Directly supported by a traceable Honda artifact or observed Honda behavior. Name the artifact and scope. |
| `EXTERNAL_PRIOR_ART` | Apple documentation or another project's verified implementation. Include URL, pinned revision/date where possible, and what it cannot prove about Honda. |
| `EXPERIMENTAL_LAB_ONLY` | A shared, extractable, non-certified credential or test asset explicitly allowed for a bounded non-production lab experiment. State its provenance and limitations; never treat it as a trusted/production credential or Honda evidence. |
| `SYNTHETIC_TEST_VALUE` | Generated test bytes/state or mocked output. Never present as captured or Honda output. |
| `HYPOTHESIS` | A reasoned design inference awaiting Honda confirmation. State the missing evidence. |
| `UNKNOWN` | Not established. Do not fill it with a plausible value silently. |

`ABSENT_LITERAL` is a search result scoped to a particular artifact and search method; it is not proof that behavior is absent. When a document compares evidence, put the class beside the claim rather than relying on a general disclaimer. Preserve source links and exact repository SHAs. Do not commit private captures, firmware, keys, or generated media.
