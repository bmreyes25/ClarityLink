"""Stable lab-only receiver identity, stored outside the repository."""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import uuid


class IdentityError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class LabIdentity:
    device_id: str
    main_uuid: str
    secondary_uuid: str


def load_or_create_identity(path: Path) -> LabIdentity:
    """Persist a synthetic local identity with owner-only permissions."""
    target = path.resolve()
    repository = Path(__file__).resolve().parents[3]
    if target == repository or repository in target.parents:
        raise IdentityError("identity_path_inside_repository")
    if target.exists():
        if target.stat().st_mode & 0o077:
            raise IdentityError("identity_permissions_too_open")
        try:
            data = json.loads(target.read_text())
            identity = LabIdentity(**data)
            uuid.UUID(identity.main_uuid)
            uuid.UUID(identity.secondary_uuid)
            if identity.main_uuid == identity.secondary_uuid or len(identity.device_id.split(":")) != 6:
                raise ValueError
            return identity
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise IdentityError("invalid_identity_file") from exc
    raw = bytearray(os.urandom(6))
    raw[0] = (raw[0] | 2) & 0xfe  # locally administered, unicast
    identity = LabIdentity(":".join(f"{value:02X}" for value in raw), str(uuid.uuid4()), str(uuid.uuid4()))
    target.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        fd = os.open(target, flags, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(identity.__dict__, stream, sort_keys=True)
    except FileExistsError:
        return load_or_create_identity(target)
    return identity
