# AltScreen control plane

Apple WWDC19 documents vehicle-selected content types for cluster streams and parallel map plus maneuver-card video. It does not publish the private UI command schema.

xcertplay's pinned `AirPlaySession.kt` handles AirPlay SETUP stream lists and capability features; it is independent receiver evidence, not the control-plane source for all implementations. Harman's `alt111` profile uses `maps:/car/instrumentcluster`; its code/config also references `/map`. URL selection and `suggestUI` / `showUI` semantics are implementation/reverse-engineering evidence, not Apple documentation. No exact Honda control messages or versions were found in the tracked Honda notes.

| Identifier / command | Role | Sender / timing | Confidence |
|---|---|---|---|
| `maps:/car/instrumentcluster` | generic cluster context | receiver profile / UI selection | observed in open implementation |
| `maps:/car/instrumentcluster/map` | map view selection | UI context transition | open-source/reverse-engineered; Honda unknown |
| `maps:/car/instrumentcluster/instructioncard` | instruction card selection | UI context transition | open-source/reverse-engineered; Honda unknown |
| `suggestUI` | candidate UI contexts | phone/receiver interaction varies by generation | exact Honda direction/timing unknown |
| `showUI` | selected screen UUID and UI context | control-plane selection | exact Honda schema unknown |
| `forceKeyFrame` | request fresh video frame | receiver-to-sender control in xcertplay's command helper; default empty params targets main stream | per-display selector and Type-111 behavior unknown |

Do not build this state machine into Honda code until a Honda trace or target-compatible source confirms the command direction, payload, and routing.
