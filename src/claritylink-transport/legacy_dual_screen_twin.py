"""Offline per-screen legacy AES/session ownership twin.

Type110 behavior is Honda-confirmed. Applying the same per-screen legacy
derivation to Type111 is an offline hypothesis supported by external prior
art and is not Honda runtime-confirmed.
"""

from __future__ import annotations

from enum import Enum
from typing import Callable

from crypto_model import BlockEncryptor, ScreenCryptoModel
from receiver_core import HondaScreenReceiverCore, ReceiverEvent
from screen_kdf import derive_honda_type110_screen_key_iv


class ScreenRole(str, Enum):
    TYPE110 = "TYPE110"
    TYPE111_SYNTHETIC = "TYPE111_SYNTHETIC"


class DuplicateStreamConnectionID(ValueError):
    """Two simultaneously owned screens were given the same stream ID."""

    code = "duplicate_stream_connection_id"

    def __init__(self, roles: tuple[ScreenRole, ScreenRole]) -> None:
        self.roles = roles
        super().__init__("streamConnectionID must be unique within a session")


class LegacyScreenInputError(ValueError):
    """Sanitized rejection raised after a screen-local input failure."""

    def __init__(self) -> None:
        super().__init__("synthetic screen input rejected")


class LegacyScreenSession:
    """Own one screen's derived key, CTR context, parser, and receiver state."""

    def __init__(
        self,
        role: ScreenRole,
        stream_connection_id: int,
        key: bytes,
        iv: bytes,
        encrypt_block: BlockEncryptor,
        max_body_size: int,
    ) -> None:
        self.role = role
        self.stream_connection_id = stream_connection_id
        self._iv = bytes(iv)
        self._active = True
        crypto = ScreenCryptoModel(key, iv, encrypt_block)
        self._receiver: HondaScreenReceiverCore | None = HondaScreenReceiverCore(
            crypto=crypto, max_body_size=max_body_size
        )

    @property
    def active(self) -> bool:
        return self._active

    def feed(self, data: bytes | bytearray | memoryview) -> list[ReceiverEvent]:
        if not self._active or self._receiver is None:
            raise RuntimeError("screen is destroyed")
        try:
            return self._receiver.feed(data)
        except Exception:
            # A parser, crypto, config, or extraction error destroys only the
            # state owned by this screen. Never include parser input in errors.
            self.destroy()
            raise LegacyScreenInputError() from None

    def reset(self) -> None:
        if not self._active or self._receiver is None:
            raise RuntimeError("screen is destroyed")
        self._receiver.reset(reset_crypto=True, iv=self._iv)

    def destroy(self) -> None:
        if not self._active:
            return
        self._active = False
        if self._receiver is not None:
            self._receiver._parser.reset()
            if self._receiver._crypto is not None:
                self._receiver._crypto.destroy()
            self._receiver._config = None
            self._receiver._config_pending = False
        self._receiver = None
        self._iv = bytes(16)

    def __repr__(self) -> str:
        return (
            f"LegacyScreenSession(role={self.role.value!r}, "
            f"stream_connection_id={self.stream_connection_id}, active={self.active})"
        )


class LegacyDualScreenTwin:
    """One immutable synthetic parent session with role-owned screen states."""

    def __init__(
        self,
        authenticated_session_material: bytes,
        *,
        encrypt_block: BlockEncryptor,
        max_body_size: int = 16 * 1024 * 1024,
        derive_screen_key_iv: Callable[[bytes, int], tuple[bytes, bytes]] =
        derive_honda_type110_screen_key_iv,
    ) -> None:
        if not isinstance(authenticated_session_material, bytes) or len(authenticated_session_material) != 16:
            raise ValueError("session material must be exactly 16 synthetic bytes")
        self._session_material = bytes(authenticated_session_material)
        self._encrypt_block = encrypt_block
        self._max_body_size = max_body_size
        self._derive = derive_screen_key_iv
        self._screens: dict[ScreenRole, LegacyScreenSession] = {}

    @property
    def roles(self) -> tuple[ScreenRole, ...]:
        return tuple(self._screens)

    def add_screen(self, role: ScreenRole, stream_connection_id: int) -> LegacyScreenSession:
        if not isinstance(role, ScreenRole):
            raise ValueError("screen role is required")
        if (
            isinstance(stream_connection_id, bool)
            or not isinstance(stream_connection_id, int)
            or not 1 <= stream_connection_id < (1 << 64)
        ):
            raise ValueError("stream_connection_id must be a nonzero uint64")
        if role in self._screens:
            raise ValueError("screen role is already active")
        for other_role, other in self._screens.items():
            if other.stream_connection_id == stream_connection_id:
                raise DuplicateStreamConnectionID((other_role, role))
        key, iv = self._derive(self._session_material, stream_connection_id)
        screen = LegacyScreenSession(
            role, stream_connection_id, key, iv, self._encrypt_block, self._max_body_size
        )
        self._screens[role] = screen
        return screen

    def screen(self, role: ScreenRole) -> LegacyScreenSession:
        try:
            return self._screens[role]
        except KeyError:
            raise KeyError("screen role is not active") from None

    def destroy_screen(
        self,
        role: ScreenRole,
        *,
        expected_screen: LegacyScreenSession | None = None,
    ) -> bool:
        """Destroy one screen, optionally requiring an exact owned instance."""
        if expected_screen is None:
            screen = self._screens.pop(role, None)
        else:
            screen = expected_screen
            if self._screens.get(role) is expected_screen:
                self._screens.pop(role)
        if screen is not None:
            screen.destroy()
            return True
        return False

    def __repr__(self) -> str:
        return f"LegacyDualScreenTwin(roles={[role.value for role in self.roles]!r})"
