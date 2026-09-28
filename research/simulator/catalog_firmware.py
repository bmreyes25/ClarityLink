#!/usr/bin/env python3
"""Allowlisted offline catalog. Never extracts firmware or emits raw runtime text."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile

MEMBERS = {
    "system.tar": ["system/bin/jmcs", "system/lib/libcarplay_proxy.so", "system/etc/media_codecs.xml"],
    "system-vendor.tar": ["system/vendor/media/mcs/j_config.xml"] + [
        f"system/vendor/app/{name}.{extension}"
        for name in ("CarPlay", "CarPlayService", "Navigation", "ExternalDisplayApService", "ExternalDisplayOutService")
        for extension in ("apk", "odex")],
}
STATES = ["01-disconnected", "02-carplay-home", "03-apple-maps-open", "04-apple-maps-routing",
          "05-route-center-music", "06-factory-cluster-navigation", "07-hondahack-casting", "08-disconnected-again"]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def catalog(root):
    if root.name != "CLARITY_FORENSIC_20260925_211500_COMPLETE_WORKING":
        raise ValueError("Use only the complete working acquisition")
    artifacts = []
    for archive_name, allowlist in MEMBERS.items():
        with tarfile.open(root / "filesystems" / archive_name) as archive:
            for name in allowlist:
                member = archive.getmember(name)
                if not member.isfile():
                    raise ValueError("Expected regular firmware member")
                with archive.extractfile(member) as stream:
                    data = stream.read()
                artifacts.append({"archive": "filesystems/" + archive_name, "member": name,
                                  "bytes": len(data), "sha256": digest(data)})
    snapshots = []
    for state in STATES:
        files = {}
        for name in ("activity.stdout.txt", "audio.stdout.txt", "display.stdout.txt", "services.stdout.txt"):
            data = (root / "runtime" / state / name).read_bytes()
            files[name] = {"sha256": digest(data), "bytes": len(data)}
        snapshots.append({"state": state, "source": "runtime/" + state, "files": files,
                          "evidence": "observed snapshot; state name is acquisition label",
                          "audioFocusOwner": "unknown; opaque snapshot, not decoded here"})
    return {"schemaVersion": 1, "source": root.name,
            "evidence": "observed file bytes; no private contents included",
            "storageRef": "forensic-storage-map.json", "serviceEvidenceRef": "service-evidence.json", "artifacts": artifacts,
            "runtimeSnapshots": snapshots,
            "limitations": ["Live filesystem archives are non-atomic", "No ARM code executed",
                            "No protocol payload or per-event audio decoded"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("working", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(json.dumps(catalog(args.working), indent=2) + "\n")
    print("Cataloged 14 allowlisted artifacts and 8 opaque runtime snapshots")
