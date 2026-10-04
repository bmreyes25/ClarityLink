# 43T1-R4A — architecture pivot matrix

**Decision frame:** useful navigation content in the cluster while stock center CarPlay remains Honda-owned. R3C forbids treating `jmcs` interposition/Type111 as the default path. `BEST_NEXT_PATH` means **best next offline architecture study**, not a Honda deployment finding. Source/API facts are detailed in [navigation audit](43t1-r4a-navigation-data-source-audit.md); Display 1 limits are in [renderer note](43t1-r4a-cluster-rendering-architecture.md).

| Architecture | Source of navigation data | Uses jmcs? | Uses Type111? | Preserves stock center CarPlay? | Cluster rendering path | Privacy risk | Legal/API risk | Offline model possible? | Main blocker | Verdict |
|---|---|---:|---:|---|---|---|---|---:|---|---|
| Turn-card-only independent cluster renderer | Synthetic/manually selected route steps first; own route provider later | No | No | Yes by separation; runtime coexistence `UNKNOWN` | Host 800×480 model; standalone API-17 `Presentation` candidate `UNKNOWN` on Honda | Low with synthetic data; rises with live location | Low for synthetic; provider terms later | Yes | No supported independent Honda Display 1 app/window path or safe-area proof | **BEST_NEXT_PATH** (offline only) |
| Own iPhone routing companion → Android renderer | Own app's destination, route, location and maneuvers | No | No | Yes by separation; runtime `UNKNOWN` | Same unproved independent display path | Medium: location plus local transfer | iOS background/local-network permissions; provider rights | Yes | Phone-to-Honda channel and app lifecycle not evidenced | KEEP_STUDYING |
| Local/self-hosted OSRM or Valhalla → renderer | OSM-derived independent route | No | No | Yes by separation; runtime `UNKNOWN` | Same unproved display path | Low to medium depending server/log retention | OSM attribution and hosting terms | Yes | Hosting/geocoding, live map matching, display entry | KEEP_STUDYING |
| Paid provider → renderer | Mapbox/Google/HERE/TomTom own API route | No | No | Yes by separation; runtime `UNKNOWN` | Same unproved display path | Medium: coordinates leave device | Pricing, caching, attribution, map/display license | Yes, with synthetic fixture | Provider contract + display entry | KEEP_STUDYING |
| Apple Maps/Waze active-route extraction | Third-party app's live maneuvers | No direct `jmcs` use | No | Unknown | Any proposed renderer | High: screen/notification capture | No reviewed public live-trip export | Synthetic only | Public data source absent | REJECT_NO_DATA_SOURCE |
| HondaHack Xposed view insertion | Any independent route source | No `jmcs` | No | Center likely separate, no proof | Known injected View in `ExternalDisplayOutService` | Depends on source | Third-party/private hook and host permissions | Yes, reference only | In-process host injection is not supported ClarityLink entry | REJECT_TOO_COMPLEX |
| Reopen Type111 `jmcs` patch/preload | iPhone CarPlay Type111 | Yes | Yes | Unproven/high risk | Honda receiver + externaldisplay | High | Unsupported interposition | Existing old models only | R3C no safe entry/cleanup | REJECT_REINTRODUCES_INTERPOSITION |

## Scope classification

- Non-Type111 turn-card renderer: `ARCHITECTURE_CANDIDATE` with current rendering **`MODEL_ONLY`**; an on-device version would `REQUIRES_NEW_APP` and a new supported Display 1 access proof.
- Own iPhone route: `REQUIRES_NEW_APP`; provider-backed variants `REQUIRES_EXTERNAL_API` (unless self-hosted/open data). All require user-controlled location and an independent communication design.
- Apple Maps/Waze mirroring or scraped maneuver extraction: `REQUIRES_UNSUPPORTED_CAPTURE`, potentially `REJECT_PRIVACY_RISK`, and `REJECT_NO_DATA_SOURCE` under reviewed public APIs.
- HondaHack output: `HONDA_OBSERVED` composition precedent, not an authorized integration dependency or a Type111 proof.

**Answer:** the remaining promising *architecture direction* is an independent, glanceable cluster guidance renderer fed by a route ClarityLink owns. Its Honda deployment path is **not yet viable/proven**. R4B should resolve offline UX/state and API-17 compatibility questions while keeping display access, safe area, and live data as explicit gates. A strong negative on independent Display 1 access would require another pivot rather than falling back to `jmcs` interposition.
