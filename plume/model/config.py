"""Paramètres utilisateur : ~/.config/plume/config.json (respecte $XDG_CONFIG_HOME)."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from .serialization import atomic_write

CONFIG_VERSION = 1


def config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / "plume" / "config.json"


def _default_favorites() -> list[dict]:
    return [
        {"tool": "fountain", "color": "#1a1a1aff", "width": 1.6},
        {"tool": "fountain", "color": "#1f5fd1ff", "width": 1.6},
        {"tool": "fountain", "color": "#d32f2fff", "width": 1.6},
        {"tool": "ballpoint", "color": "#2e7d32ff", "width": 1.2},
        {"tool": "pencil", "color": "#4a4f57ff", "width": 1.0},
    ]


@dataclass
class Config:
    vault_path: str = ""
    favorites: list[dict] = field(default_factory=_default_favorites)
    recent_colors: list[str] = field(default_factory=list)
    custom_colors: list[str] = field(default_factory=list)
    # Courbe de pression : points (pression brute → facteur), interpolés linéairement.
    pressure_curve: list[list[float]] = field(default_factory=lambda: [[0.0, 0.15], [0.5, 0.6], [1.0, 1.0]])
    active_favorite: int = 0
    highlighter: dict = field(default_factory=lambda: {"tool": "highlighter", "color": "#ffe0668c", "width": 14.0})
    eraser: dict = field(default_factory=lambda: {"mode": "stroke", "size": 12.0, "highlight_only": False})
    straight_highlighter: bool = False
    pressure_sensitivity: float = 0.5
    default_background: str = "blank"
    side_button_action: str = "eraser"   # eraser | lasso
    finger_draws: bool = False
    hover_dot: bool = True
    shape_recognition: bool = True
    companion_pdf: bool = True
    autosave_delay_ms: int = 3000
    lasso_mode: str = "free"  # free | rect
    note_template: str = ""   # PDF modèle (feuille lignée, Cornell…) des nouvelles notes ; vide = fond simple
    x11_mode: bool = True   # XWayland : curseur toujours caché sous GNOME (pris en compte au redémarrage)
    recent_files: list[str] = field(default_factory=list)
    config_version: int = CONFIG_VERSION

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        """Charge la config ; un fichier absent ou illisible donne les valeurs par défaut."""
        path = path or config_path()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        if not isinstance(data, dict):
            return cls()
        defaults = cls()
        kwargs = {}
        for f in fields(cls):
            value = data.get(f.name, getattr(defaults, f.name))
            # Une valeur du mauvais type (édition à la main) retombe sur la valeur par défaut.
            kwargs[f.name] = value if type(value) is type(getattr(defaults, f.name)) else getattr(defaults, f.name)
        return cls(**kwargs)

    def save(self, path: Path | None = None) -> None:
        path = path or config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(asdict(self), ensure_ascii=False, indent=2).encode()
        atomic_write(path, lambda fh: fh.write(payload))
