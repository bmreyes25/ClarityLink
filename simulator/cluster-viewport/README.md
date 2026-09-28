# Cluster navigation viewport twin

Open [`index.html`](index.html) directly in Safari or another Mac browser. It is an offline, synthetic rendering of the candidate navigation rectangle; no vehicle, network, or captured phone image is used.

The presentation scales a **584 × 191 logical-pixel image region** inside the observed **800 × 480 HDMI display**. The 584 × 215 parent and 24-pixel top padding come from the copied Honda Hack `meter_civic.xml` cast layout; they are not an OEM declaration of the native Navigation page's safe area. The physical photos show the mirrored image in the central gauge region, but do not provide a panel-pixel calibration. Accordingly, the profile leaves the factory rectangle's physical origin, boundaries, pixel encoding, and native transport unresolved. This is a bounded digital-twin viewport, not a claim that its proxy edges are exact factory edges.

`viewport-profile.json` is the machine-readable record of measured, inferred, and unknown properties. The synthetic maneuver and map geometry are illustrative only.
