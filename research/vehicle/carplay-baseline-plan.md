# Stock CarPlay baseline plan — V8

## Purpose and limits

Only consider a future passive observation of an already-existing, ordinary parked CarPlay session. Record visible navigation source/page, whether a cluster navigation page is already present, and any naturally occurring display handoff or session ending. Do not initiate/disconnect/reconnect a session, change settings, select another app, intercept USB/network traffic, inspect private authentication material, hook or replace `jmcs`, launch a competing receiver, or provoke warnings.

The observation may describe visible stock behavior and lifecycle. It cannot establish Type111 negotiation, stream identity, a delegated session key, an authenticated route/maneuver ingress, app-to-Honda permissions, or a safe custom window. Do not infer custom secondary-navigation support from normal CarPlay operation.

## Existing evidence and decision

P1-C5 remains `P1_C5_NO_GO_PENDING_NEW_INTERFACE_EVIDENCE`. `jmcs` owns stock USB/iAP2, authentication, Type110, and control in the reviewed artifacts; no supported external Type111 or authenticated guidance subscriber is established. The PlayPort 43P two-stream observation is limited to its lab profile. V8 cannot close the P1 gate and is ranked below V0/V1–V5 unless a specific visible lifecycle question is written down first.

V8 is not a ready session experiment: no iPhone session is authorized in this planning milestone, and there is no new session evidence to collect now. If later approved, use direct observation only; record user-visible facts, local observation time with uncertainty, and optional camera media privately. Avoid screen recording APIs, USB traces, network traces, protocol captures and personal navigation details unless a separate lawful/privacy review authorizes a narrow collection.

## Stop conditions

Stop observation for any unexpected warning, abnormal cluster/center display, vehicle movement, operator distraction, session instability, user privacy concern, or request to alter connection/settings. Do not attempt recovery through reconnect, reboot, battery disconnect, or another receiver. Preserve only minimal private evidence and end the session safely.
