"""Small, abstract window-order model for Test 4B.

This models ordering claims only. It has no Honda coordinates, no Android
SurfaceFlinger connection, and no code path to a vehicle display.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class Owner(str, Enum):
    HONDA_BOTTOM = "honda_bottom"
    HONDA_NAVIGATION = "honda_navigation"
    HONDA_INTERRUPT = "honda_interrupt"
    APP_PRESENTATION = "app_presentation"
    CLARITY_IN_HONDA_NAV = "clarity_in_honda_nav"
    GAUGE_MODULE = "gauge_module"


@dataclass(frozen=True)
class Layer:
    owner: Owner
    z: int
    opaque: bool = True
    same_changeable_region: bool = True


@dataclass(frozen=True)
class Warning:
    name: str
    owner: Owner
    z: int | None
    same_changeable_region: bool = True


@dataclass(frozen=True)
class SceneResult:
    presentation_visible: bool
    obscured_warnings: tuple[str, ...]
    unknown_warnings: tuple[str, ...]
    modeled_safe: bool
    provenance: str = "MODEL_ONLY"


def evaluate(layers: Iterable[Layer], warnings: Iterable[Warning]) -> SceneResult:
    """Evaluate if modeled opaque app content can cover each warning.

    Larger z means later/topmost composition. An unknown warning z is never
    treated as protected. This deliberately does not model OEM tie-breaking.
    """
    stack = tuple(layers)
    renderer_layers = tuple(x for x in stack if x.owner in
                            (Owner.APP_PRESENTATION, Owner.CLARITY_IN_HONDA_NAV))
    if not renderer_layers:
        raise ValueError("scene requires a ClarityLink content layer")
    presentation = renderer_layers[-1]
    visible = not any(x.opaque and x.z > presentation.z and
                      x.same_changeable_region for x in stack
                      if x.owner not in (Owner.APP_PRESENTATION, Owner.CLARITY_IN_HONDA_NAV))
    obscured: list[str] = []
    unknown: list[str] = []
    for warning in warnings:
        if warning.z is None:
            unknown.append(warning.name)
            continue
        if warning.same_changeable_region and any(
            renderer.opaque and renderer.z > warning.z and renderer.same_changeable_region
            for renderer in renderer_layers
        ):
            obscured.append(warning.name)
    return SceneResult(visible, tuple(obscured), tuple(unknown),
                       not obscured and not unknown)


def api17_aosp_scenario(app_z: int = 2) -> SceneResult:
    """Model app type 2 beneath Honda-reported type-2006 roots (layer 18).

    The layer values are AOSP API17 for the app, plus Honda-root facts from
    prior static research. The combined stack is a hypothesis, not proof that
    Honda runs unmodified policy.
    """
    return evaluate(
        [Layer(Owner.HONDA_BOTTOM, 18), Layer(Owner.HONDA_NAVIGATION, 18),
         Layer(Owner.HONDA_INTERRUPT, 18), Layer(Owner.APP_PRESENTATION, app_z)],
        [Warning("Honda interrupt warning", Owner.HONDA_INTERRUPT, 18),
         Warning("warning owner/stack not identified", Owner.HONDA_NAVIGATION, None)],
    )


def scenario_between_main_and_interrupt() -> SceneResult:
    return evaluate(
        [Layer(Owner.HONDA_BOTTOM, 10), Layer(Owner.HONDA_NAVIGATION, 18),
         Layer(Owner.APP_PRESENTATION, 19), Layer(Owner.HONDA_INTERRUPT, 20)],
        [Warning("warning inside main content", Owner.HONDA_NAVIGATION, 18),
         Warning("interrupt-root warning", Owner.HONDA_INTERRUPT, 20)],
    )


def scenario_above_interrupt() -> SceneResult:
    return evaluate(
        [Layer(Owner.HONDA_NAVIGATION, 18), Layer(Owner.HONDA_INTERRUPT, 20),
         Layer(Owner.APP_PRESENTATION, 30)],
        [Warning("interrupt-root warning", Owner.HONDA_INTERRUPT, 20)],
    )


def scenario_honda_owned_content() -> SceneResult:
    return evaluate(
        [Layer(Owner.HONDA_BOTTOM, 10), Layer(Owner.HONDA_NAVIGATION, 18),
         Layer(Owner.CLARITY_IN_HONDA_NAV, 18), Layer(Owner.HONDA_INTERRUPT, 20)],
        [Warning("interrupt-root warning", Owner.HONDA_INTERRUPT, 20)],
    )


def scenario_meter_warning() -> SceneResult:
    return evaluate(
        [Layer(Owner.HONDA_NAVIGATION, 18), Layer(Owner.APP_PRESENTATION, 2),
         Layer(Owner.GAUGE_MODULE, 100)],
        [Warning("independent gauge-module warning", Owner.GAUGE_MODULE, 100)],
    )


def scenario_mixed_warning_owners() -> SceneResult:
    return evaluate(
        [Layer(Owner.HONDA_NAVIGATION, 18), Layer(Owner.APP_PRESENTATION, 19),
         Layer(Owner.HONDA_INTERRUPT, 18), Layer(Owner.GAUGE_MODULE, 100)],
        [Warning("Android interrupt warning", Owner.HONDA_INTERRUPT, 18),
         Warning("gauge-module warning", Owner.GAUGE_MODULE, 100)],
    )
