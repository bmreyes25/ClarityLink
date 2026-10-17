"""MODEL_ONLY receiver ownership checks; no protocol, I/O, or credential handling.

These fail-closed checks express evidence requirements for architecture reviews.
Passing them does not mean iOS, Honda, or any accessory accepts the topology.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Topology(str, Enum):
    ONE_RECEIVER_TWO_STREAMS = "one-receiver-two-streams"
    TWO_RECEIVERS_SHARED_SESSION = "two-receivers-shared-session"
    TWO_RECEIVERS_TWO_SESSIONS = "two-receivers-two-sessions"
    DELEGATED_MEDIA_ENDPOINT = "delegated-media-endpoint"
    METADATA_SUBSCRIBER = "metadata-subscriber"
    INDEPENDENT_COMPANION = "independent-companion"


@dataclass(frozen=True)
class OwnershipClaim:
    topology: Topology
    usb_owners: frozenset[str] = frozenset({"Honda"})
    iap2_owners: frozenset[str] = frozenset({"Honda"})
    auth_owners: frozenset[str] = frozenset({"Honda"})
    control_owners: frozenset[str] = frozenset({"Honda"})
    primary_owners: frozenset[str] = frozenset({"Honda"})
    secondary_owner: str | None = None
    primary_session: str = "stock"
    secondary_session: str | None = None
    primary_generation: int = 1
    secondary_generation: int | None = None
    distinct_authorized_identity: bool = False
    second_session_permission_proven: bool = False
    iap2_multiplex_contract_proven: bool = False
    wireless_discovery_proven: bool = False
    secondary_transport: str = "shared-wired"
    delegation_contract_proven: bool = False
    external_content_contract_proven: bool = False
    secondary_security_proven: bool = False
    setup_valid: bool = False
    type111_requested: bool = False
    secondary_listener_ready: bool = False
    no_apk_admission_proven: bool = False
    stock_type110_active: bool = True


def validate_claim(claim: OwnershipClaim) -> tuple[str, ...]:
    """Return model reasons; empty means internally consistent, never deployable."""
    errors: list[str] = []
    if not isinstance(claim.topology, Topology):
        errors.append("unsupported_topology")
    if not isinstance(claim.primary_session, str) or not claim.primary_session:
        errors.append("invalid_primary_session_identity")
    if claim.secondary_owner is not None and (
        not isinstance(claim.secondary_session, str) or not claim.secondary_session
    ):
        errors.append("invalid_secondary_session_identity")
    if (isinstance(claim.primary_generation, bool) or
            not isinstance(claim.primary_generation, int) or claim.primary_generation < 1 or
            (claim.secondary_generation is not None and
             (isinstance(claim.secondary_generation, bool) or
              not isinstance(claim.secondary_generation, int) or claim.secondary_generation < 1))):
        errors.append("invalid_generation")
    if claim.usb_owners != frozenset({"Honda"}):
        errors.append("conflicting_usb_owner")
    split_iap2_proven = (
        claim.topology is Topology.TWO_RECEIVERS_TWO_SESSIONS and
        ((claim.secondary_transport == "shared-wired" and claim.iap2_multiplex_contract_proven) or
         (claim.secondary_transport == "independent-wireless" and claim.wireless_discovery_proven))
    )
    if claim.iap2_owners != frozenset({"Honda"}) and not split_iap2_proven:
        errors.append("conflicting_iap2_owner")
    if claim.primary_owners != frozenset({"Honda"}) or not claim.stock_type110_active:
        errors.append("stock_type110_not_preserved")
    if not claim.auth_owners or len(claim.auth_owners) > 1 and not claim.distinct_authorized_identity:
        errors.append("conflicting_accessory_identity")
    if not claim.control_owners or len(claim.control_owners) > 1 and not claim.second_session_permission_proven:
        errors.append("duplicate_control_owner")

    if claim.topology is Topology.ONE_RECEIVER_TWO_STREAMS:
        if (claim.auth_owners != frozenset({"Honda"}) or
                claim.control_owners != frozenset({"Honda"}) or
                claim.secondary_owner != "Honda"):
            errors.append("single_receiver_ownership_mismatch")
    elif claim.topology in (Topology.TWO_RECEIVERS_SHARED_SESSION, Topology.DELEGATED_MEDIA_ENDPOINT):
        if (claim.auth_owners != frozenset({"Honda"}) or
                claim.control_owners != frozenset({"Honda"}) or
                claim.secondary_owner != "ClarityLink"):
            errors.append("delegated_owner_mismatch")
    elif claim.topology is Topology.TWO_RECEIVERS_TWO_SESSIONS:
        if (claim.auth_owners != frozenset({"Honda", "ClarityLink"}) or
                claim.control_owners != frozenset({"Honda", "ClarityLink"}) or
                claim.secondary_owner != "ClarityLink"):
            errors.append("independent_owner_mismatch")
        if claim.secondary_transport == "shared-wired":
            if not claim.iap2_multiplex_contract_proven or claim.iap2_owners != frozenset({"Honda", "ClarityLink"}):
                errors.append("iap2_multiplex_unproven")
        elif claim.secondary_transport == "independent-wireless":
            if not claim.wireless_discovery_proven or claim.iap2_owners != frozenset({"Honda", "ClarityLink"}):
                errors.append("wireless_link_unproven")
        else:
            errors.append("unsupported_secondary_transport")
    elif claim.topology in (Topology.METADATA_SUBSCRIBER, Topology.INDEPENDENT_COMPANION):
        if (claim.auth_owners != frozenset({"Honda"}) or
                claim.control_owners != frozenset({"Honda"}) or
                claim.secondary_owner != "ClarityLink"):
            errors.append("companion_owner_mismatch")
    else:
        errors.append("unsupported_topology")

    secondary = claim.secondary_owner is not None
    if claim.topology in (Topology.ONE_RECEIVER_TWO_STREAMS, Topology.TWO_RECEIVERS_SHARED_SESSION,
                          Topology.DELEGATED_MEDIA_ENDPOINT):
        if secondary and claim.secondary_session != claim.primary_session:
            errors.append("secondary_session_mismatch")
        if secondary and claim.secondary_generation != claim.primary_generation:
            errors.append("stale_session_generation")
    if claim.topology is Topology.TWO_RECEIVERS_TWO_SESSIONS:
        if claim.secondary_session is None or claim.secondary_session == claim.primary_session:
            errors.append("duplicate_session_identity")
        if not claim.distinct_authorized_identity or not claim.second_session_permission_proven:
            errors.append("second_session_unproven")
    if claim.topology in (Topology.TWO_RECEIVERS_SHARED_SESSION, Topology.DELEGATED_MEDIA_ENDPOINT):
        if not claim.delegation_contract_proven:
            errors.append("delegation_unproven")
    if claim.topology is Topology.METADATA_SUBSCRIBER:
        if claim.type111_requested:
            errors.append("metadata_not_video")
        if not claim.external_content_contract_proven or not claim.no_apk_admission_proven:
            errors.append("metadata_subscriber_unproven")
    if claim.topology is Topology.INDEPENDENT_COMPANION:
        if claim.type111_requested:
            errors.append("companion_not_type111")
        if not claim.external_content_contract_proven:
            errors.append("independent_data_path_unproven")
    if secondary and claim.type111_requested:
        if not claim.setup_valid:
            errors.append("malformed_or_unsupported_setup")
        if not claim.secondary_security_proven:
            errors.append("secondary_security_unproven")
        if not claim.secondary_listener_ready:
            errors.append("secondary_listener_unavailable")
    return tuple(dict.fromkeys(errors))


@dataclass
class ModelLifecycle:
    """Synthetic primary/secondary failure isolation and idempotent cleanup."""

    primary_active: bool = True
    secondary_active: bool = False
    resources: list[str] = field(default_factory=list)
    closed: list[str] = field(default_factory=list)

    def start_primary(self) -> bool:
        if self.primary_active:
            return False
        self.primary_active = True
        return True

    def start_secondary(self, *, setup_valid: bool, security_ready: bool, listener_ready: bool) -> bool:
        if not self.primary_active or self.secondary_active:
            return False
        acquired: list[str] = []
        try:
            if not setup_valid:
                return False
            if not security_ready:
                return False
            acquired.append("security")
            if not listener_ready:
                return False
            acquired.append("listener")
            self.resources.extend(acquired)
            self.secondary_active = True
            return True
        finally:
            if not self.secondary_active:
                self.closed.extend(reversed(acquired))

    def stop_secondary(self) -> None:
        self.secondary_active = False
        self.closed.extend(reversed(self.resources))
        self.resources.clear()

    def stop_primary(self) -> None:
        self.stop_secondary()
        self.primary_active = False
