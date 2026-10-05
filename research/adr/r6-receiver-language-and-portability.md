# R6 ADR — receiver language and portability

Decision: keep Python as the host protocol/reference and fixture oracle; plan a C/C++ implementation for Honda API17/ARMv7/Bionic. Share sanitized semantic fixtures, not Python runtime objects. No target native receiver has been built yet.

The target is Android 4.2.2/API17 on ARMv7/Tegra3. Python's host FFmpeg subprocess, `plistlib`, Tk/PNG sinks and loopback lab sockets are unsuitable as a stock receiver service. Native code can bind target socket, codec and Surface APIs; it introduces memory-safety and ABI risks, so parsing must keep R5Z bounds and use host ASan/UBSan before any target consideration. A target build alone would not prove USB/iAP2/MFi, audio, controls, Display0/1 or lifecycle.
