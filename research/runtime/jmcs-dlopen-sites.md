# jmcs dynamic-loading sites

**HONDA CONFIRMED (bounded static search):** jmcs imports `dlopen`/`dlsym`/`dlclose`. Prior focused reverse engineering located call families near VA `0x121aec` and `0x18d9ba` in generic dynamic/SQLite extension support. String and code evidence identifies SQLite's `sqlite3_load_extension` / `unixDlOpen` / extension APIs; no AirPlay function-name lookup string, vendor plugin directory, CarPlay config-selected module, or `/info` lookup is established.

Exact argument provenance for every callsite is not re-derived here because the preserved generated disassembly lacks linker-call annotations and this environment has no ARM disassembler. Existing Step 31 work establishes no known dynamic lookup of `AirPlayCopyServerInfo`; it is absent `.dynsym`. Classify the SQLite extension path as a general data-driven extension capability whose enablement/configuration/reachability from jmcs inputs remains UNKNOWN, not a legitimate controlled Honda CarPlay load seam. Security-sensitive arbitrary extension loading is not a deployment option.

No confirmed property/environment/directory-controlled Honda plugin load exists in the audited evidence. Failure behavior for generic SQLite load is returned through SQLite extension errors; it is not a stock receiver plugin failure path.
