"""Typology derivation (Member 3). Contract Section 8.

typologies  = distinct pattern types of a cluster's hits
              + SCATTER_GATHER when a FAN_OUT hit and a FAN_IN hit exist where
                >= 50% of the fan-out receivers are also fan-in senders.
primary     = highest severity: CYCLE > PASS_THROUGH > SCATTER_GATHER > FAN_OUT > FAN_IN
Ground-truth columns are never read here.
"""
from __future__ import annotations

from typing import Iterable

from app.contracts import PatternHit

SEVERITY_ORDER: list[str] = ["CYCLE", "PASS_THROUGH", "SCATTER_GATHER", "FAN_OUT", "FAN_IN"]
SCATTER_GATHER_MIN_OVERLAP = 0.5


def _counterparties(hit: PatternHit) -> set[str]:
    """Receivers of a FAN_OUT / senders of a FAN_IN: all accounts except the focal one."""
    return {a for a in hit.accounts if a != hit.focal_account}


def has_scatter_gather(hits: Iterable[PatternHit]) -> bool:
    hits = list(hits)
    fan_outs = [h for h in hits if h.pattern_type == "FAN_OUT"]
    fan_ins = [h for h in hits if h.pattern_type == "FAN_IN"]
    for fo in fan_outs:
        receivers = _counterparties(fo)
        if not receivers:
            continue
        for fi in fan_ins:
            overlap = len(receivers & _counterparties(fi)) / len(receivers)
            if overlap >= SCATTER_GATHER_MIN_OVERLAP:
                return True
    return False


def derive_typologies(hits: Iterable[PatternHit]) -> list[str]:
    """Distinct typologies of a cluster, ordered by severity (most severe first)."""
    hits = list(hits)
    found = {h.pattern_type for h in hits}
    if has_scatter_gather(hits):
        found.add("SCATTER_GATHER")
    return [t for t in SEVERITY_ORDER if t in found]


def primary_typology(typologies: Iterable[str]) -> str:
    """Most severe typology. Raises ValueError for an empty collection."""
    present = set(typologies)
    for t in SEVERITY_ORDER:
        if t in present:
            return t
    raise ValueError("a cluster needs at least one typology")
