# R7C6 emulator ownership proof

The harness inventory was empty before each launch. It selected an available
even port in 5580–5680, created a unique `r7c6_api17_<pid>-<epoch>` AVD under
the ignored build directory, and launched the pinned Intel emulator itself.
The completed smoke identified API 17, Android 4.2.2, x86 ABI, qemu=1, and the
exact AVD name through the emulator console. The only ADB target was the
expected `emulator-<port>` in `device` state. Installation and activity launch
occurred after those checks.

Cleanup terminated only the launched emulator PID, removed only its unique AVD
directory and `.ini`, and left no ADB target. It did not use `adb kill-server`,
`killall`, or `pkill`. The unowned `emulator-5580` seen before R7C6 was not
targeted; each R7C6 run began only after the ADB inventory was empty.
