# Display 1 rendering contract — post P2-C6

**State:** conditional architecture contract; not vehicle-ready. Applies to a future public Android `Presentation` client only unless an OEM adapter provides a separate reviewed contract. It preserves Honda ownership of existing graphics and does not grant any current Honda access.

## Required Android caller and context

The public API17 implementation must run inside a Package Manager registered Android application process. The component obtains `DisplayManager` from a framework `Context`, selects the intended currently valid display, derives a display context, and presents through a WindowManager window with a valid app window token. The verified ClarityLink probe used an `Activity`; a bare shell/native process has no Android Activity, application `Context`, or app window token. `dumpsys display` under shell UID 2000 is a diagnostic path only. It does not produce these objects or confer application identity. No process may impersonate another UID or bypass signature, SELinux, Binder, or WindowManager checks.

Generic public `Presentation` does not inherently require Honda's signature in AOSP API17, but Honda's modified policy, app install rules, permission grants, and actual caller admission remain unknown. Do not add `SYSTEM_ALERT_WINDOW` or request signature permissions as a speculative workaround. If the exact OEM policy requires a privilege unavailable to a normal app, stop and require a legitimate OEM-supported interface or separately approved deployment design.

## Output invariants

1. **No frame before admission:** identify the exact Display 1 by fresh observation and explicit selector; fail if absent, ambiguous, invalid, or different from the authorized target.
2. **No frame before geometry:** load a reviewed, versioned physical/logical transform and approved safe rectangle. Unknown boundaries, unknown rotation/scaling, or invalid measurements withdraw rendering.
3. **Bound the actual window/surface:** render only inside the approved rectangle. Alpha-zero pixels outside a full-frame window are insufficient proof of non-occlusion.
4. **Preserve Honda ownership:** do not replace, reparent, or cover the stock bottom/main/interrupt roots, Type110 path, or critical vehicle indicators. The allowed overlap and z-order require measured, OEM-supported evidence.
5. **Warning preemption:** a higher-priority warning or interrupt must clear and suspend ClarityLink content before it is obscured. Resume only when the warning ends and the surface, display identity, and geometry are revalidated.
6. **Lifecycle:** clear on route/session stop, surface loss, display removal, app stop, process death, and teardown. Framework app-window reclamation is necessary but not proof of safe Honda service restoration.
7. **No persistence by default:** no startup registration, system package replacement, receiver patch, root, Xposed, framebuffer use, or configuration change. Any deployment mechanism and its cleanup require separate explicit approval.

## Acceptance evidence before visible rendering

All gates are conjunctive:

- Exact Honda model/build/API identity and package/artifact hashes.
- Separately approved deployment architecture; if app-based, an explicitly authorized APK hash, package name, signing identity, requested permissions, install/removal plan, and UID record.
- Fresh ordinary-app display enumeration and a separately reviewed `Presentation` admission result on that exact build; a `dumpsys display` inventory does not satisfy this gate.
- Exact caller permission/admission outcome, valid window token, app-window bounds, effective display context, and no displacement of Honda roots.
- OEM safe-region coordinates and transform, or a separately authorized calibrated observation with warning/interrupt states and known physical boundaries.
- Warning precedence and preemption/withdrawal behavior.
- Surface loss, display removal, app crash/death, and stock graphics restoration evidence.
- A frozen no-retry test plan, rollback/recovery procedure, private evidence format, and a fresh single-use authorization for the exact operation.

Until every gate passes, the required state is `NO_GO_FOR_VISIBLE_RENDERING`; the output backend remains offline/mock-only. The P2-C4 synthetic safe-area model does not satisfy Honda geometry. The P2-C5 shell diagnostic does not satisfy window admission.

## Option recommendation

Under current restrictions there is no rendering path: the shell query is read-only inventory; the existing OEM Binder is control/status; and public Presentation requires an app context/window token. If the user explicitly changes the no-APK constraint, a temporary unprivileged APK using public Presentation is the most direct **admission experiment**, because it creates a legitimate Android app identity and context. It is not a rendering GO. A documented OEM additive display adapter is the preferred long-term product boundary if Honda provides one. No OEM adapter was found in the reviewed artifacts.

Separate approvals are required for relaxing the no-APK restriction, installing any package, attempting a Honda window admission, submitting visible pixels, and uninstalling or changing system state. Approval for one step does not imply approval for the next.
