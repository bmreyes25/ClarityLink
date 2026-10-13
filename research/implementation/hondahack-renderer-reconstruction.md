# CL-IMP-01 — HondaHack renderer behavior reconstruction

**Status:** static behavior mapping complete; ClarityLink-owned API17 host simulator implemented.
**Evidence boundary:** HondaHack prior art and existing repository static records only. No Honda or iPhone was accessed for this milestone.

## Reconstructed behavior

The preserved trace describes two separate paths that meet at HondaHack's custom view:

```text
Display 0 screenshot source
  -> 400 × 240 ARGB_8888 bitmap
  -> 384,000-byte MemoryFile / duplicated PFD through Messenger
  -> HondaHack handler reconstructs bitmap
  -> custom ImageView
  -> Xposed inserts custom view into Honda ExternalDisplay root
  -> Display 1 / downstream cluster composition
```

The external-display process owns three full-window roots: bottom, main content, and interrupt/warning. HondaHack resolves the main/interrupt roots in-process and inserts its custom view. The casting image occupies a 584 × 191 region in one HondaHack layout whose root is 584 × 215. Those dimensions are layout-local observations and do not define the physical visible cluster rectangle. The outer Android display is documented as 800 × 480; physical masking and safe map bounds remain unresolved.

## Function-to-simulator mapping

| Observed HondaHack behavior | ClarityLink-owned equivalent | Status and limit |
|---|---|---|
| Android View / ImageView contains supplied pixels | `HondaStyleDisplayHostSimulator` exposes a dedicated custom-content container for one project-owned View | Implemented on public Android View APIs; no production frame decoder attached yet. |
| View inserted in main root above bottom content | Separate bottom and navigation roots with an explicit priority enum and deterministic child order | Implemented in the simulator; root represents only its own Activity. |
| Interrupt root takes visual priority | Independent simulated stock-warning TextView/root above navigation | Implemented and emulator-tested; not Honda warning behavior evidence. |
| Navigation/meter mode controls content lifecycle | Navigation inactive removes content and clears its session generation | Implemented; re-entry cannot restore a prior frame. |
| Start/stop cast messages add/remove content | Generation-checked attach/detach with a one-child bound | Implemented; stale generation cannot detach a newer view. |
| MemoryFile/PFD transports captured bitmap | No screenshot capture copied. Future ClarityLink frame IPC will use a separate bounded Type111 frame contract. | Deliberately not copied: the target is authentic Type111, not a Display 0 mirror. |
| Xposed resolves Honda `InterfaceWindow` and calls `addView` | Host simulator constructs its own roots inside a ClarityLink Activity | Implemented without Honda package access, Xposed, private APIs, or stock-process modifications. |
| Honda full-window roots use 800 × 480 logical display | Simulator uses the Activity's measured bounds | No Honda viewport is inferred from this layout. |

## Simulator behavior contract

- Root layers are ordered bottom content < navigation content < warning interrupt.
- ClarityLink may attach only one unparented View to an active navigation page and positive generation.
- Warning visibility withdraws navigation content from view; a new attach is rejected while the warning is active.
- Leaving Navigation removes the project View and resets its generation.
- A mismatched generation cannot remove the active content.
- `close()` removes simulator-owned views idempotently; calls that would mutate a closed simulator fail closed.
- The stock warning source is a simulated, project-owned `TextView`; it does not invoke a car API.

## Existing evidence and references

- [HondaHack display path](../hondahack/hondahack-display-path.md) records the call path, bitmap dimensions, IPC, layout dimensions, and live correlation limits.
- [HondaHack static analysis](../hondahack/hondahack-static-analysis.md) records symbols, methods, roots, and provenance.
- [ClarityLink output interface](../hondahack/CLARITYLINK_OUTPUT_INTERFACE.md) states that host-root acquisition is a skeleton and safe physical geometry is unknown.
- [ExternalDisplay host flow](../display/externaldisplay-host-flow.md) documents in-process roots, Binder boundary, and lifecycle.
- API17 behavior will be exercised through the isolated public-API emulator probe. Its results establish only the project-owned simulator and generic Android Views.

## Not established

This reconstruction does not establish that ClarityLink can enter Honda's ExternalDisplay process, that Honda exports a view/frame Binder API, that Honda accepts Type111, or that the HondaHack viewport corresponds to the physical cluster safe area. The private hook mechanism is not reproduced against Honda. No screenshot of Display 0 is used as a Type111 source.
