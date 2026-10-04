# R5Y — symbolic Display 1 sink contract

The `DisplaySink` Protocol accepts only `DisplayFrame` model values and can clear/close. `MockDisplay1Sink` stores one symbolic frame, generation, frame count, clear reason, and closed flag. It does not create pixels, windows, surfaces, Android `Presentation`, SurfaceFlinger state, framebuffer output, or Honda Display 1 content.

The core clears on stale in-generation sequence, lost source, reroute, explicit stale/session-death signal, decoder/media error, generation teardown, and session supersession. A frame from an old or future generation is rejected before it can touch the current sink. The sink rejects a mismatched generation or updates after close. Cleanup closes the sink before decoder/security/listener resources.

This tests a desired fail-clear *model* contract only. R4D still lacks proof of ordinary-app admission, the physical navigation viewport, warning priority, safe z-order, and stock coexistence. The mock sink cannot establish cluster compatibility or driving safety.
