# 43T1-R4D — ordinary-app Display 1 admission gate

**Gate state: `NOT_AUTHORIZED`.** Current research verdict is `R4D_ORDINARY_APP_DISPLAY1_POSSIBLE_BUT_UNPROVEN`.

No install, app launch, display enumeration on Honda, `Presentation.show()`, ADB session, or vehicle experiment is authorized. A future proposal must first provide offline evidence for every item below and then a separate exact plan with explicit user authorization:

1. Known package/signing requirements, including whether normal app signing is sufficient.
2. Known effective permission grants for required window type; manifest requests alone do not count.
3. Known Display 1 enumeration and display-context path for an ordinary app on the exact Honda framework/build.
4. Known public `Presentation`/window creation and denial behavior on that framework.
5. Known display removal, app stop/crash, window dismissal/removal, and service lifecycle behavior.
6. Known z-order and warning/interrupt limitations; authoritative physical viewport/transform and protected warning/status boundaries.
7. No HondaHack/Xposed, `jmcs`, Type111, framebuffer write, or persistent system change.
8. A separately reviewed exact future experiment plan with stop/recovery criteria and explicit user authorization.

All gates are conjunctive. Missing or contradictory evidence keeps the gate `NOT_AUTHORIZED`; success on AOSP or a bench display is not Honda admission proof. @ECC reviewed the gate against Rules v2, R3C, the R4C safe-area boundary, and the R4D permission evidence.
