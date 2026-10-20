# Development setup

ClarityLink combines Python analysis and tests, a JavaScript offline simulator, and Android/API17 source and build tools. Not every toolchain is needed for documentation or host-only work.

1. Clone the repository and read [current status](../status/current.md) and [contribution guidance](../../CONTRIBUTING.md).
2. For the configured host suite, install `requirements-test.txt` in a local Python environment and use Node.js as described in the [test guide](../development/testing.md).
3. For API17 builds, follow the exact pinned toolchain and offline build instructions in the relevant milestone report and [tools guide](../../tools/README.md). Record tool versions and artifact hashes.
4. Keep generated outputs, private captures, credentials, firmware, and personal data out of Git.

CI does not run Honda tests, live iPhone tests, or ADB/emulator operations. See [safety and vehicle testing](../safety/vehicle-testing.md) before proposing any such work.
