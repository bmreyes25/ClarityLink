"""Host-only preserved-image inventory check; never executes archive members."""
from __future__ import annotations

import hashlib
import tarfile
from pathlib import Path

MEMBER = "system/bin/netcfg"
MAX_BINARY = 65536
HONDA_NETCFG_SHA256 = "ea204431f664a32e44d890373ccf16c952a921e2c98cd5e0387b2bbc429c00db"


def inspect_archive(path: Path) -> dict:
    """Return bounded static inventory evidence; unreadable/ambiguous means unresolved."""
    try:
        with tarfile.open(path, "r") as archive:
            matches = [member for member in archive if member.name.removeprefix("./") == MEMBER]
            if not matches:
                return {"status": "HONDA_PRESERVED_NETCFG_ABSENT"}
            if len(matches) != 1 or not matches[0].isfile() or matches[0].size > MAX_BINARY:
                return {"status": "HONDA_PRESERVED_NETCFG_UNRESOLVED"}
            stream = archive.extractfile(matches[0])
            if stream is None:
                return {"status": "HONDA_PRESERVED_NETCFG_UNRESOLVED"}
            data = stream.read(MAX_BINARY + 1)
            if len(data) != matches[0].size or not data.startswith(b"\x7fELF"):
                return {"status": "HONDA_PRESERVED_NETCFG_UNRESOLVED"}
            digest = hashlib.sha256(data).hexdigest()
            return {
                "status": "HONDA_PRESERVED_NETCFG_PRESENT",
                "path": MEMBER,
                "mode": oct(matches[0].mode),
                "uid": matches[0].uid,
                "gid": matches[0].gid,
                "size": matches[0].size,
                "sha256": digest,
                "known_binary": digest == HONDA_NETCFG_SHA256,
            }
    except (OSError, tarfile.TarError):
        return {"status": "HONDA_PRESERVED_NETCFG_UNRESOLVED"}
