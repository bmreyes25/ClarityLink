"""Pure copy-on-write serverInfo display augmentation."""
from copy import deepcopy
from collections.abc import Mapping
from typing import Any
from models import ClarityLinkCapabilityProfile

class ServerInfoError(ValueError): pass

class ClarityLinkServerInfoAugmentor:
    def __init__(self, profile: ClarityLinkCapabilityProfile): self.profile = profile
    def augment(self, server_info: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(server_info, Mapping): raise ServerInfoError("serverInfo must be a mapping")
        result = deepcopy(dict(server_info))
        if not self.profile.enabled: return result
        displays = result.get("displays")
        if not isinstance(displays, (list, tuple)): raise ServerInfoError("displays must be an array")
        cluster = self.profile.descriptor.as_dict()
        identity = cluster.get("uuid")
        if any(not isinstance(d, Mapping) for d in displays): raise ServerInfoError("each display must be a mapping")
        # Idempotence covers both UUID-keyed and deliberately opaque profiles.
        if any(dict(d) == cluster for d in displays): return result
        if identity is not None and any(d.get("uuid") == identity for d in displays):
            raise ServerInfoError("secondary UUID must be independent")
        result["displays"] = [*deepcopy(list(displays)), cluster]
        return result
