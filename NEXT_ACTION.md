# Next action

**Continue Step 4 offline:** reconstruct the minimum second-display Identification/session advertisement from the existing Honda CarPlay static model and record the required descriptor fields and unresolved bytes. Do not use the vehicle or begin live negotiation.

The HondaHack Android output path is now traced to a regular View hosted inside Honda's ExternalDisplay window. The host renderer prototype is available at src/claritylink-renderer/, but its API 17 backend needs privileged host integration and the physical Navigation viewport remains unmeasured.

Current reports:

- research/hondahack/hondahack-display-path.md
- research/hondahack/hondahack-static-analysis.md
- research/hondahack/CLARITYLINK_OUTPUT_INTERFACE.md
- research/iap2-identification.md

Keep raw captures/APKs local and ignored. No framebuffer access or vehicle write is part of the next step.
