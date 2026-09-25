"""Reproduce Honda Hack hook-name recovery using only copied backup files.

The extracted app_process was modified by Honda Hack; its static AES key is
read from the file, never printed. No ARM code or vehicle service is run.
"""
import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE = ROOT / "research/decompiled/cn.autohack.hondahack-2/sources/cn/autohack/hondahack/Hb.java"
PROCESS = ROOT / "extracted/system-vendor/system/bin/app_process"
OUT = ROOT / "research/search/hondahack-hook-targets.json"

key = PROCESS.read_bytes()[0x6000:0x6010]
if len(key) != 16:
    raise RuntimeError("Copied app_process is incomplete")
source = SOURCE.read_text()
arrays = re.findall(r"public static final byte\[\] ([\w$]+) = \{([^}]+)\};", source)
names = {}
for field, values in arrays:
    encrypted = bytes(int(number.strip()) % 256 for number in values.split(","))
    transformed = bytes((byte - 6) % 256 for byte in encrypted)[::-1]
    proc = subprocess.run(["openssl", "enc", "-d", "-aes-128-ecb", "-K", key.hex(), "-nopad"],
                          input=transformed, capture_output=True, check=True)
    plain = proc.stdout
    pad = plain[-1]
    if pad < 1 or pad > 16 or plain[-pad:] != bytes([pad]) * pad:
        raise RuntimeError("Invalid padding in " + field)
    names[field] = plain[:-pad].decode("utf-8")
if len(names) != 283:
    raise RuntimeError(f"Expected 283 names, found {len(names)}")
OUT.write_text(json.dumps(names, indent=2, ensure_ascii=False) + "\n")
print(f"Recovered {len(names)} hook names")
