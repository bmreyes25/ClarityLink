# One parked Clarity session: evidence checklist

**Purpose:** collect only evidence missing from the September 18 session. That session already captured a CarPlay reconnect and paired Maps/Music screenshots, so repeating it unchanged would waste car time. This is a measurement session, not a firmware install. Allow up to 10 minutes with the car parked and ventilation appropriate for the power state. The user may toggle the existing Honda Hack casting setting for one comparison; ask before doing that later if the earlier no-vehicle-change rule still applies.

## Have ready before powering the car

- Mac with the current `clarity-analysis` workspace and `adb` available; same Wi-Fi network as Wirebug. Disable a VPN if it blocks local access.
- iPhone and a reliable CarPlay USB cable. An Apple Maps route is useful for the physical-cluster photo, but no second reconnect is needed just to collect the same ordinary logs.
- A way to photograph the *physical* instrument cluster from the driver's seat. The saved HDMI screenshot does not include every physical cluster element.
- Honda Hack casting **off** for the baseline; cluster set to its Navigation page. Leave the car in Park.

## Sequence in the car

1. Power the head unit, open Wirebug, and note the `adb connect` address it currently displays. Tell me if it differs from `192.168.86.102:5555`.
2. Connect the iPhone, start Apple Maps guidance, and select the cluster Navigation page. Switch the center to Music while the route remains active.
3. Photograph the *physical* cluster with its surrounding gauges and warning area. Say whether a spoken direction is audible. Capture the center Music/cluster Navigation state with casting **off** using `twin-survey`.
4. If approved for this session, enable the already installed Honda Hack casting, photograph the physical cluster again, and run `twin-survey` a second time. Confirm spoken directions still work. Restore casting to its original state after this comparison. No factory navigation setter or vehicle-bus command is used.
5. I will run the prepared `process-inventory` and `capability-survey` read-only captures: current `jmcs` process, accessible `/proc` memory-map and file-descriptor listings, Unix/TCP socket inventories, kernel configuration if exposed, and whether USB tracing is already mounted and readable. Permission-denied results are recorded and left alone.
6. Leave CarPlay connected until the inventory completes, then the car can be turned off. A second unplug/reconnect is reserved for a later diagnostic with a proven new way to observe the actual negotiation; ordinary logcat alone already failed to expose it.

## Mac-side capture prepared before the session

The capture is bounded and saved only under `research/captures/`. The process-inventory phase reads `ps`, `/proc/net/unix`, `/proc/net/tcp`, and, where permissions allow, `/proc/<jmcs-pid>/{status,maps,fd}`. The capability survey reads `/proc/mounts`, `/proc/config.gz`, `/proc/modules`, and lists existing `/sys/kernel/debug` paths. `twin-survey` reads display, SurfaceFlinger, window/activity, audio/media, service, and process snapshots plus one screenshot from each Android display. It does not invoke `su`, mount anything, clear logs, change properties, install software, start a daemon, send a broadcast, or touch vehicle buses. Socket inventories can include local connection details and stay on this Mac. Any unsupported read is recorded as unavailable rather than worked around with a vehicle write.

From the analysis root, use one distinct output directory per casting state; never run two phases into the same phase folder:

```sh
python3 research/scripts/cluster_readonly_capture.py --serial 192.168.86.102:5555 --output research/captures/SESSION-twin-off --phase twin-survey
python3 research/scripts/cluster_readonly_capture.py --serial 192.168.86.102:5555 --output research/captures/SESSION-twin-on --phase twin-survey
python3 research/scripts/cluster_readonly_capture.py --serial 192.168.86.102:5555 --output research/captures/SESSION-inventory --phase process-inventory
python3 research/scripts/cluster_readonly_capture.py --serial 192.168.86.102:5555 --output research/captures/SESSION-capabilities --phase capability-survey
```

Replace `SESSION` with a UTC timestamp and the serial with Wirebug's current address. If time runs short, prioritize the physical off/on photos and two `twin-survey` captures, then the capability survey; existing static and September 18 evidence already cover many ordinary logs.

Back on the Mac, compare the two saved surveys without reconnecting to the vehicle:

```sh
python3 research/scripts/twin_survey_compare.py --off research/captures/SESSION-twin-off/twin-survey --on research/captures/SESSION-twin-on/twin-survey --output research/captures/SESSION-twin-diff.json
```

The diff records hashes, unavailable commands, and a bounded set of changed display/audio/service lines. Changed text is evidence of state differences, not proof that a layer or audio route belongs to a particular CarPlay protocol stream.

## Questions this session can and cannot answer

The physical photo can bound the navigation safe area. Comparing the two `twin-survey` snapshots can reveal display layers, app/service ownership, and audio routing visible to Android; it cannot fully emulate proprietary cluster electronics. The `/proc` inventory may identify the receiver's loaded libraries and open IPC/network endpoints. None of these captures reveals the contents of iAP2 identification packets or proves decoder concurrency. Those require a separately prepared, reviewable diagnostic; do not prolong this session trying the same ordinary log capture again.
