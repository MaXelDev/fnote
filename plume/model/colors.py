"""Couleurs : normalisation HEX, couleurs récentes, palettes par défaut."""
from __future__ import annotations

import re

_HEX = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
MAX_RECENT = 8

INK_PALETTE = [  # 16 encres lisibles sur page blanche (contraste ≥ 3,79:1)
    "#1a1a1a", "#4a4f57", "#37474f", "#1b2a6b", "#1f5fd1", "#00838f", "#2e7d32", "#1b4d2b",
    "#6b6b00", "#d32f2f", "#8e1b3a", "#e65100", "#6d4321", "#6a3fb5", "#5b2160", "#c2185b",
]
HIGHLIGHTER_PALETTE = ["#ffe066", "#9be58a", "#ff9ecb", "#8fd0ff", "#ffbf73"]
HIGHLIGHTER_ALPHA = 0x8c  # ≈ 55 %


def normalize(value: str, alpha: int | None = None) -> str | None:
    """« abc », « #aabbcc », « #aabbccdd » → « #aabbccdd » (minuscules) ; None si invalide."""
    m = _HEX.match(value.strip()) if isinstance(value, str) else None
    if not m:
        return None
    h = m.group(1).lower()
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) == 6:
        h += "ff"
    if alpha is not None:
        h = h[:6] + f"{max(0, min(255, alpha)):02x}"
    return "#" + h


def rgb(value: str) -> str:
    """« #aabbccdd » → « #aabbcc »."""
    return normalize(value)[:7]


def push_recent(recents: list[str], color: str, limit: int = MAX_RECENT) -> list[str]:
    """Ajoute en tête, sans doublon (comparaison sur la couleur opaque), plafonné."""
    c = normalize(color)
    if c is None:
        return list(recents)
    out = [c] + [r for r in recents if normalize(r) and rgb(r) != rgb(c)]
    return out[:limit]
