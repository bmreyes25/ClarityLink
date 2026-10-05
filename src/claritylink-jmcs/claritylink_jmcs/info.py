"""Complete-shape host /info assembly with explicit evidence boundaries."""
from __future__ import annotations

from dataclasses import dataclass
import plistlib
from typing import Any, Mapping

from .capabilities import SecondaryDisplayCapability, host_info
from .identity import LabIdentity


class InfoError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class InfoProfile:
    identity: LabIdentity
    name: str
    model: str
    manufacturer: str
    source_version: str
    feature_bits: int
    audio_formats: tuple[Mapping[str, Any], ...]
    audio_latencies: tuple[Mapping[str, Any], ...]
    hid_devices: tuple[Mapping[str, Any], ...]
    displays: SecondaryDisplayCapability = SecondaryDisplayCapability()


def build_info(profile: InfoProfile) -> dict[str, Any]:
    """Require caller-supplied audio/HID facts; never invent host capabilities."""
    if any(not isinstance(value, str) or not 1 <= len(value) <= 128
           for value in (profile.name, profile.model, profile.manufacturer, profile.source_version)):
        raise InfoError("invalid_info_identity")
    if isinstance(profile.feature_bits, bool) or not 0 <= profile.feature_bits < 2**64:
        raise InfoError("invalid_info_features")
    if not profile.audio_formats or not profile.audio_latencies or not profile.hid_devices:
        raise InfoError("audio_hid_capabilities_required")
    if len(profile.audio_formats) > 32 or len(profile.audio_latencies) > 32 or len(profile.hid_devices) > 32:
        raise InfoError("info_capability_count_exceeded")
    for item in profile.audio_formats:
        if not isinstance(item, Mapping) or not all(key in item for key in
                ("type", "audioType", "audioOutputFormats")) or not isinstance(item["audioOutputFormats"], int):
            raise InfoError("invalid_audio_format")
    for item in profile.audio_latencies:
        if not isinstance(item, Mapping) or not all(key in item for key in
                ("type", "inputLatencyMicros", "outputLatencyMicros")):
            raise InfoError("invalid_audio_latency")
    for item in profile.hid_devices:
        if not isinstance(item, Mapping) or not all(key in item for key in
                ("uuid", "name", "displayUUID", "hidDescriptor", "hidProductID", "hidVendorID", "hidCountryCode")):
            raise InfoError("invalid_hid_capability")
        if item["displayUUID"] != profile.identity.main_uuid or not isinstance(item["hidDescriptor"], bytes) or not 1 <= len(item["hidDescriptor"]) <= 4096:
            raise InfoError("invalid_hid_capability")
    capability = SecondaryDisplayCapability(
        width=profile.displays.width, height=profile.displays.height, fps=profile.displays.fps,
        enabled=profile.displays.enabled, physical_width_mm=profile.displays.physical_width_mm,
        physical_height_mm=profile.displays.physical_height_mm,
        main_uuid=profile.identity.main_uuid, secondary_uuid=profile.identity.secondary_uuid,
        initial_url=profile.displays.initial_url)
    info = host_info(capability)
    info.update({"sourceVersion": profile.source_version, "features": profile.feature_bits,
                 "model": profile.model, "manufacturer": profile.manufacturer,
                 "deviceID": profile.identity.device_id,
                 "bluetoothIDs": [profile.identity.device_id], "name": profile.name,
                 "rightHandDrive": False, "keepAliveLowPower": False,
                 "keepAliveSendStatsAsBody": False,
                 "audioFormats": list(profile.audio_formats),
                 "audioLatencies": list(profile.audio_latencies),
                 "hidDevices": list(profile.hid_devices)})
    try:
        wire = plistlib.dumps(info, fmt=plistlib.FMT_BINARY)
    except (TypeError, ValueError, OverflowError) as exc:
        raise InfoError("info_not_serializable") from exc
    if len(wire) > 1_000_000:
        raise InfoError("info_too_large")
    return info


def validate_info_shape(info: Mapping[str, Any]) -> tuple[str, ...]:
    required = ("sourceVersion", "features", "statusFlags", "model", "manufacturer", "deviceID",
                "bluetoothIDs", "name", "modes", "audioFormats", "audioLatencies", "hidDevices", "displays")
    missing = [key for key in required if key not in info]
    displays = info.get("displays")
    if not isinstance(displays, list) or not displays:
        missing.append("displays[primary]")
    else:
        kinds = [entry.get("type") for entry in displays if isinstance(entry, Mapping)]
        if 110 not in kinds:
            missing.append("displays[110]")
        if 111 not in kinds:
            missing.append("displays[111]")
        for entry in displays:
            if not isinstance(entry, Mapping):
                missing.append("displays[entry]")
                continue
            for key in ("uuid", "widthPixels", "heightPixels", "widthPhysical", "heightPhysical", "maxFPS", "viewAreas"):
                if key not in entry:
                    missing.append(f"displays[].{key}")
    return tuple(sorted(set(missing)))
