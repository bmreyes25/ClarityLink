# REA Android analysis toolchain

This guide describes a bounded, offline REA/JADX setup for authorized APK inspection. It does not authorize APK execution, vehicle access, Honda ADB, private service calls, patching, or injection. Keep private artifacts and evidence outside the public repository.

## Readiness layers

Treat these states separately:

1. **INSTALLED:** the binary or provider file exists.
2. **CONFIGURED:** REA has a persistent provider path and Java environment.
3. **RUNTIME VERIFIED:** REA actually performed the requested operation on a harmless APK.
4. **OPTIONAL:** an auxiliary tool not needed for the current analysis.
5. **MISSING / INCOMPATIBLE:** a required prerequisite is absent or does not match the pinned integration.
6. **REQUIRES USER ACTION:** the running desktop MCP process must be restarted or reloaded to inherit updated configuration.

## Prerequisites and pinned provider

Use a full JDK 17 or newer with `jdk.compiler`; prefer the JDK version supported by the installed REA release. For the currently documented integration, confirm the current pinned provider release and SHA-256 in the [REA Android guide](https://github.com/morluto/rea/blob/main/docs/android-analysis.md) and [REA third-party provider notes](https://github.com/morluto/rea/blob/main/third_party/README.md) before installing. This campaign verified `jadx-headless-mcp` 0.7.1 against the documented SHA-256 `6e5eacf500b64292bfb73c49797c1958f6ee44646e43e868039ae7feb573ff75`.

Install only from the linked official release, in a user-owned isolated directory. Verify the digest before the JAR is used. Do not disable verification or run a mismatched file. Preserve existing Codex MCP configuration and add only the REA-specific provider/JDK settings required by current official setup instructions.

## Read-only doctor

Run `tools/doctor_re_toolchain.sh` to check host architecture, REA, Java/Javac/compiler module, pinned provider digest, REA configuration, and optional Apktool/Ghidra/Android SDK utilities. The check does not install software, edit configuration, execute APK contents, or prove that a running MCP server inherited current settings.

To exercise REA CLI on a harmless self-authored APK:

```sh
tools/doctor_re_toolchain.sh --smoke-apk /path/to/self-authored.apk
```

This bounded smoke mode requests package inspection and reports only operation status and Evidence IDs. Perform focused class/method/reference calls through the currently supported REA interfaces and preserve their Evidence output in authorized private storage. Never use HondaHack as the first smoke target.

## MCP restart and validation

After changing persistent REA configuration, restart or reload Codex Desktop using its supported UI, then make a fresh live Android inspection call on the harmless APK. A successful REA CLI call, a registered MCP server, or a file existing on disk is not proof that the desktop MCP can execute Android operations. Report MCP readiness only after an actual live Android tool call succeeds.

## Apktool and Android SDK tools

Apktool is optional when REA/JADX provides the required manifest and resource decoding. Android SDK tools such as `aapt`, `apksigner`, or `adb` are not automatically required for offline static inventory. Do not install or invoke unnecessary tools. Never use Apktool to patch or repackage the subject artifact.

## Evidence and privacy

Record tool versions, provider digest, harmless target identity, operations executed, operation results, and Evidence IDs. Keep private paths, artifact hashes, raw outputs, signing data, decompiled code, and proprietary call graphs in authorized private storage. Public reports should contain only sanitized architecture and limitations.
