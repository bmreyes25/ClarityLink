# 43T1-R1 repository evidence-language audit

**Scope:** repository Markdown search for claims that could conflate Honda behavior, Type111, listener behavior, runtime execution, and CF semantics with offline models or external references. R1 does not rewrite historical reports; it updates current scope records and the present verifier description.

## Search and decisions

| Claim family | Audit outcome |
|---|---|
| Honda proof | Current summaries inspected use explicit static/live/model limits. R1 labels AOSP and Apple behavior as references, not Honda evidence. Historical scoped claims remain in place. |
| Type111 proof | Existing records continue to say Type111 is not accepted/proven on Honda; no R1 evidence promotes it. |
| Listener proof | D4 binding input remains a policy input only; host socket tests are labeled host/model; Honda listener reachability remains unknown. |
| Runtime proof | Existing runtime notes and reports describe host models as non-runtime proof. This milestone adds no runtime evidence. |
| CF proof | Public CoreFoundation documentation is now explicitly `EXTERNAL_REFERENCE`. Honda CFLite callback/getter ownership is listed as partial/unknown. |
| Historical CF callback wording | `PROJECT_STATE.md` summarizes the later Step 43G static callback-table finding; the linked CF callback note also preserves a Step 43H uncertainty/correction chronology. R1 does not flatten that history. R2 must re-open the hash-matched disassembly and reconcile the timeline before treating the project-side child-entry ownership contract as resolved. |

## Current wording updated

- `research/runtime/43t1-restoration-verifier.md` now distinguishes PREP2 historical readiness from the stronger R1 evidence contract and explicitly says no target read or write is proven.
- New R1 readiness and analysis records identify D4 as read-only network-policy input, never listener reachability or Type111 proof.
- No historical report was rewritten or weakened. Existing claims retain their scoped evidence labels and links.

## Limit

Text search is not a formal proof that every sentence is perfectly scoped. In particular, historical project-state entries may summarize evidence from their own time. The current R1 readiness record is the controlling fresh status and preserves unknowns rather than inheriting stale PASS labels. Repository-wide matched phrases were reviewed for scope; no historical claim was rewritten.
