# 43T1-R4D — warning and z-order static evidence

## Preserved facts

- Honda `ExternalDisplayOutService` statically creates bottom, main and interrupt roots, each full-frame `MATCH_PARENT` with window type 2006. Honda's root ownership and the roots' independent lifecycle are visible in preserved source. (`HONDA_STATIC`)
- Existing saved WindowManager/SurfaceFlinger observations associate these full-frame layers with HDMI Display 1. They do not establish ordering against a hypothetical ordinary-app window. (`HONDA_READ_ONLY_OBSERVED`)
- Factory Navigation, interrupt, meter, phone, audio and bottom guide content use Honda-owned roots. Warning/interrupt views may be placed in an interrupt root. (`HONDA_STATIC`)
- Paired physical photograph and Display 1 capture show physical indicators/status absent from the logical Display 1 frame. Downstream composition/cropping is an inference; exact transform and protected pixel bounds remain unknown. (`HONDA_READ_ONLY_OBSERVED` / `INFERENCE`)
- API17 AOSP `PhoneWindowManager` defines permission checks and type priority classes; it does not establish Honda's modified policy, layer ordering in this system, or downstream cluster composition. (`AOSP_API17_DOCUMENTED`)

## Explicit unknowns

The repository cannot establish whether warnings are composed inside Display 1 or downstream, whether downstream hardware has higher warning priority, whether a separate `Presentation` could cover a warning/interrupt root, what ordering applies among independent type-2006 windows, or whether Honda has package-specific priority policy. No safe physical region can be derived from the saved full-frame screenshots or HondaHack's layout-local geometry.

**Safety result:** warning-preserving region and safe z-order are **not proven**. An ordinary app window could be invisible, cover Honda content, or obscure a warning; no future trial is justified until the exact app-window and warning behavior is documented with authoritative evidence and the physical boundary is known. @ECC review rejects guessed regions and framework-only extrapolation.
