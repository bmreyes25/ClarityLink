# Step 2 — Factory navigation viewport and offline twin

**Status: viewport twin delivered; exact factory safe rectangle remains unmeasured.** This step completes the evidence-bounded Mac representation, but the success criterion for an *accurately calibrated native factory rectangle* is not fully met because the saved material does not expose its physical pixel boundaries.

## Evidence and geometry

- The receiver's copied `system/vendor/media/mcs/j_config.xml` sets the CarPlay screen to 800×480 pixels and 30 FPS (`ScreenProperties`, lines 165–168). Saved Android display inventories and HDMI frames identify two Android logical displays, built-in and HDMI, at 800×480. This gives a landscape logical canvas, not the meter's physical pixel format.
- `research/simulator/working-backup/meter_civic.xml` defines a 584×215-pixel root (line 2). Its `screen_cast_layout` starts 24 pixels down and contains a match-parent ImageView with `fitXY` (lines 74–75). This yields an inferred 584×191 cast-image rectangle at x=0,y=24 inside the meter layout. It is the Honda Hack casting layout, not a factory Navigation API contract.
- The saved physical photos show the mirror in the central gauge area below speed and above the lower Menu/trip values. Existing photo registration yields camera-photo quadrilaterals for cast content, but no calibrated panel pixels or guaranteed safe-edge clearance (`research/simulator/display-geometry.js`). Therefore no transformation from photo coordinates to the cluster framebuffer is asserted.
- The candidate rendering path is an Android view on the HDMI/ExternalDisplay destination. `ExternalDisplayOutService`, Navigation APIs, `disp_com_meter` and cluster helpers are the relevant next static trace set. The actual final physical meter transfer format/protocol remains unknown; do not treat an HDMI Surface or an H.264 decode output as that transport.

Pixel format: unknown for the Android-to-meter link. Saved screen PNGs are RGB captures, which only describe the capture format. Panel scaling and any final rotation/mirroring are also unverified. The twin uses a 584:191 aspect-preserving display over an 800×480 context and labels those choices in its profile.

## Delivered twin

`simulator/cluster-viewport/` contains a no-dependency Mac-browser test window with a synthetic map, route stripe and maneuver card, plus `viewport-profile.json` with the coordinate assumptions and unknowns. Open `index.html` locally. It uses only synthetic SVG pixels, does not read a vehicle capture, and does not contact the car.

## Exit check

The dimensions and cast placement assumptions are reproducible from the copied configuration/layout, and the twin deliberately confines synthetic content to the candidate rectangle. The *native factory Navigation rectangle itself* is not established by this evidence. To finish physical calibration later, obtain a matched HDMI capture and perpendicular, full-cluster photo of the **factory Navigation page**, with enough visible bezel/known geometry to fit the HDMI image to panel coordinates; then test the native UI's actual inset/safe bounds. This requires a separate parked-car capture and is not inferred from the current mirror photos.
