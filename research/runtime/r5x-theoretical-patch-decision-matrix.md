# R5X — theoretical patch decision matrix

**MODEL_ONLY / NOT_DEPLOYABLE.** Verdicts apply under current Rules v2 and R3C; a static research verdict grants no vehicle action. Legal/licensing risk is a research classification, not legal advice.

| Path | Evidence required | What it can prove | What it cannot prove | Safety risk | Vehicle risk | Legal/licensing risk | Repo value | Current verdict |
|---|---|---|---|---|---|---|---|---|
| Do nothing / keep Type111 parked | Current R3C/R4C record | Preserves current gate | Original goal | Low | None | Low | Keeps scope clear | PARKED_PENDING_NEW_EVIDENCE |
| Continue R4D Display 1 admission research | Honda policy and app-grant artifacts | Static admission constraints | Visible safe app window | Low offline | None offline | Artifact provenance needed | High | BEST_NEXT_STATIC_RESEARCH |
| Build host-only Type111 patch sandbox | Synthetic model and tests | Desired state/ownership contract | Honda compatibility | Low if bounded | None | Low with invented data | High | SAFE_MODEL_ONLY |
| Search for Honda descendant Type111 binary | Lawfully available, provenance-checked artifact | Possible static Type111 architecture | Current target behavior or authorization | Low offline | None offline | Medium; artifact rights matter | High | PARKED_PENDING_NEW_EVIDENCE |
| Design real jmcs patch | New Honda-specific schema/security/entry/ownership evidence and high-risk review | Potential design feasibility | Safe installation or live function | High | High | High | Conditional | REJECT_CURRENT_CONSTRAINTS |
| Attempt real jmcs patch | Separate high-risk review, exact plan and authorization after all technical gates | Bounded target observation only | General safety or product readiness | Critical | Critical | High | No current value | REJECT_DEPLOYMENT_RISK |
| Attempt callback replacement | Proof of stock callback forwarding, lifetime and high-risk review | Possible callback behavior | Additive safe ownership | Critical | High | High | Low | REJECT_CURRENT_CONSTRAINTS |
| Attempt LD_PRELOAD/startup mutation | Proven loader path, restoration, high-risk review | Load behavior only | Type111 acceptance and cleanup | Critical | Critical | High | Low | REJECT_DEPLOYMENT_RISK |
| Attempt HondaHack/Xposed path | Independent supported ownership and high-risk review | Host-process output behavior | Supported receiver/Type111 lifecycle | High | High | Medium/high | Low | REJECT_CURRENT_CONSTRAINTS |

R5X recommends **no real `jmcs` patch path**. The separate [R4D/R5A research](r4d-r5a-rules-v2-compliance-check.md) contains existing static next-step context; R5X adds no new Honda evidence.
