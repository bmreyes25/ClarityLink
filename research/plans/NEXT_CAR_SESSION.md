# Next parked session — readiness and short checklist

**Do not schedule another ordinary ADB/logcat session for native CarPlay display discovery.** The saved September 18/25 captures already establish the center/HDMI behavior, service topology, Waze positive control, and dual-decoder fixture result. Repeating those captures will not expose raw iAP2 Identification or a second-stream negotiation.

## Prepare on the Mac before using the car

1. Select a non-mutating iPhone-to-head-unit USB capture method that preserves the working wired CarPlay connection and records payload bytes, not just transfer counts. Verify its link speed, connector path, timestamps, and file format on the bench. A Mac-to-head-unit ADB cable is not this capture path.
2. Prepare and test a parser that retains undecoded bytes and separates **iAP2 Identification / Route Guidance** from **CarPlay display capability and stream setup**. Do not infer field names from third-party code without matching observed bytes.
3. Prepare the exact capture start/stop commands, a finite time limit, a storage estimate, privacy handling, and a recovery step that simply removes the analyzer and reconnects the iPhone. Review the setup before putting it in the car.
4. Separately, if needed, build a background-safe codec probe and test its full install/run/uninstall path offline. The earlier two-decoder fixture did not test coexistence with active CarPlay.

## Once the capture method is ready, parked-car steps

1. Verify the Clarity is parked, USB Role **Host / Port 1**, Honda Hack casting off, and Wi-Fi ADB available. Leave safety-related menus and vehicle buses untouched.
2. Connect the inline capture path between the iPhone and the normal CarPlay USB port; start a bounded capture **before** reconnecting the phone.
3. Reconnect once, wait until CarPlay is stable, start an Apple Maps route, then switch the center to Music. Record the physical cluster and audible voice state. Stop the trace.
4. Remove the capture hardware; reconnect the iPhone directly and verify center CarPlay, spoken guidance, and the normal cluster Navigation view. Hash and store raw bytes locally.

**Required result:** a decoded, checksum-validated Identification message and separate CarPlay display setup evidence, or an explicit explanation of why the trace cannot be decoded. If the proposed method cannot meet the Mac-side readiness steps, there is no reason to keep the car powered for this question. The current USB-C–to–USB-A Mac cable did not enumerate wired ADB and cannot observe the iPhone–head-unit exchange.
