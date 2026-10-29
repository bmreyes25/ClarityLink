# CL-HONDA-111-01 / M6 — Critical factory boundaries: GO / NO-GO

Offline. `safeForHonda() == false`. This document decides whether either of the two gates the project depends on has a supported pathway. It does not authorize, schedule or describe the execution of any vehicle operation. Evidence labels are those of the [evidence map](../../research/honda/cl-honda-111-01-evidence-map.md).

**Verdict: both gates are NO-GO.** Neither has a supported pathway in the preserved evidence. No speculative enabling code was written.

## Gate 1 — Authenticated Type111 admission by the existing Honda receiver

*Can the factory receiver legitimately create and maintain a Type111 child stream while Type110 continues?*

| Item | Finding |
|---|---|
| **Current verified evidence** | The receiver, session, master material, `/info` builder, Setup loop, KDF helper and CTR primitive are all in one process (`HONDA_STATIC_CONFIRMED`). Setup skips a `type:111` entry without error or response change; teardown ignores it; the proxy registers one screen sink (`HONDA_STATIC_CONFIRMED`). Two shipping external implementations (Audi MHI2Q, Harman MHI2) prove the *shape* of a receiver-resident child on other QNX builds (`EXTERNAL_SOURCE_CONFIRMED`). |
| **Strongest feasible design** | Candidate 1 in the [architecture decision](cl-honda-111-01-receiver-architecture.md): code resident in the receiver process, stock Setup called first, additive child with its own listener, key context, decoder and teardown, appended to a copy of the response. Consumer side modelled and tested (`type111_child_authority.py`). |
| **Missing source-level facts** | (1) A supported way for any non-factory code to run at the Setup branch or to extend `/info`. (2) The `/info` second-display schema and feature tokens this receiver generation needs for the phone to offer a second stream. (3) The Type111 SETUP request and response shape on Honda. (4) The Type111 key derivation, its inputs and permission to use the parent's material. (5) Whether VideoConfig is protected (conflicting external evidence, evidence-map C2). (6) A parent-loss signal usable per child; the one existing destroyed-event is a single global slot with no session identity. (7) A second decoder-and-sink registration the singleton proxy does not offer. |
| **Can preserved backups answer it?** | No for items 1, 6, 7: the preserved binaries show their **absence**, which is the answer. Items 2–5 describe what the phone sends and expects from *this* receiver, which no preserved artifact contains. |
| **Does another private artifact hold the answer?** | The public Audi and Harman source tell us what a *modern iOS sender* required from *their* receivers (`EXTERNAL_AUTHOR_REPORTED` for the phone side). That informs design; it is not Honda evidence and must not fill a Honda field by assumption. |
| **Could a separately approved read-only vehicle observation answer it?** | **No.** Stock Honda never advertises a second display, so the phone is not expected to offer Type111 and a passive log of the unsupported-type branch would stay silent. Learning the phone-to-Honda exchange requires the receiver to advertise a second stream, which is an active change. |
| **Would active integration be required?** | Yes. Any answer to items 2–5 on the real receiver requires interposing or modifying factory receiver code. |
| **Permission and safety implications** | Touching the authenticated receiver process risks Type110 CarPlay, audio, touch and the authentication session itself. It involves factory-owned authentication state and copies of session-derived keys inside the same process. No supported boundary exists, and no authorization to create one has been given. |
| **GO / NO-GO** | **NO-GO.** Conditions G1–G7 of the architecture document are all open. Offline software cannot flip any of them. |

## Gate 2 — Navigation-pane frame admission through a Honda-owned mechanism

*Can decoded frames be presented in the cluster's Navigation page without compromising the factory display?*

| Item | Finding |
|---|---|
| **Current verified evidence** | The host owns three full-frame windows on an existing Display 1 and rebuilds only on a valid display (`HONDA_STATIC_CONFIRMED`). Display 1 captures are full-frame 800×480 in every state while the physical cluster shows indicators absent from them (`HONDA_PRIOR_RUNTIME`). Pages are addressed by a contents identifier plus status that the host requests and reports through a CPU-communication service shared with B-CAN messages (`HONDA_STATIC_CONFIRMED`). HondaHack's view follows that pair and is added to an interrupt-layer or main-layer root; one Door Open warning preempted and restored it (`HONDAHACK_STATIC`, `HONDA_PRIOR_RUNTIME`, single sample). |
| **Strongest feasible design** | An authorized, host-owned frame sink implementing the `Display1OutputBackend.Host` seam that already exists in the merged API17 renderer, reporting page and interrupt state by callback and granting a revocable, generation-bound lease. ClarityLink's consumer contract for this is implemented and tested (`navigation_pane_host.py`, `type111_pane_bridge.py`). |
| **Missing source-level facts** | (1) An authorized caller identity and registration contract for any third-party View or frame. (2) The physical Navigation aperture and Display 1 to panel transform (`UNKNOWN`). (3) A reviewed warning-precedence guarantee under third-party content. (4) What the controller does with the page request and the displaying handshake, and what the request does on the vehicle side. (Who selects the page is now known: the controller.) (5) Behaviour of injected content across display loss, root recreation and host restart. (6) Reliable stock restoration, including after an abnormal exit. |
| **Can preserved backups answer it?** | Partly, for the Android side only. This campaign's bounded static trace of the host's content manager (research P1) answered item 4 for the Java side: the cluster controller selects the page and the host follows a steering-switch status record, with a waiting-then-displaying handshake back to the controller. What the controller does with it, and any effect of the page request on the vehicle, are not in the preserved set and cannot be derived offline. |
| **Does another private artifact hold the answer?** | The Door Open sequence and the Display 1/physical photo pair are the only physical records. They cover one warning and full-frame capture, not aperture, page exit and re-entry, other warning classes or host loss. |
| **Could a separately approved read-only observation answer it?** | In part. A synchronized external recording of the center display and the cluster through ordinary page changes can estimate visible pixel correspondence for that state, and a read-only host state read can confirm which page identifier and status the host reports. It cannot grant authorization, expose controller arbitration, or prove precedence. See the [observation plan](cl-honda-111-01-next-observation-plan.md). |
| **Would active integration be required?** | Yes, for admission itself. Putting any ClarityLink content into the host means running code in the host process (HondaHack's mechanism) or sending page requests to the CPU-communication service. Both are active. |
| **Permission and safety implications** | The only demonstrated path runs inside a factory process through a private hook with no declared caller identity. Its page claim is an interrupt request on a service that also carries B-CAN data, with vehicle-side effect unknown. Warning dominance has one observed sample and no guarantee. A guessed rectangle risks covering indicators. Independent vehicle-safety review does not exist. |
| **GO / NO-GO** | **NO-GO.** `DISPLAY_SUPPORTED_PATH_NOT_FOUND` stands. |

## What the campaign changed

- The "Navigation page" is now defined at the level the host actually uses (contents identifier plus status, requested and reported through a CPU-communication service), so future observation requests can be written in those terms.
- The HondaHack placement logic is documented at role level: root choice, index, visibility rule, stop behaviour. Six design rules follow from it, implemented and tested in the pane host.
- The VideoConfig protection question is shown to be genuinely open, with conflicting evidence, instead of assumed.
- One earlier open item (HondaHack teardown, U-20) is partly resolved statically.

## What it did not change

Neither gate moved from NO-GO. The campaign found no new fact that makes either one supported; it found additional reasons the page claim needs review as a vehicle-bus-adjacent operation.

## Different existing-hardware approaches with a distinct evidence path

The brief asks whether any such approach exists without revisiting rejected ideas. One does, and it is **not** the finish line: the factory cluster already accepts structured turn-by-turn data through its own navigation interfaces. That path has separate evidence (report 06) and a separate, flagged bus-output risk (CL-R10B). It is the structured-guidance capability the brief says does not satisfy genuine Type111 video, so it is recorded here and not pursued. No other approach with a distinct evidence path was found.
