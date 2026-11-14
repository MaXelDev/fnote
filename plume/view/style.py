"""Feuille de style Qt (QSS) centralisée, générée depuis resources/tokens.json."""
from __future__ import annotations

import json
from functools import cache
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

TOKENS_PATH = Path(__file__).resolve().parent.parent / "resources" / "tokens.json"


@cache
def tokens() -> dict:
    return json.loads(TOKENS_PATH.read_text(encoding="utf-8"))


def scheme() -> str:
    """« dark » ou « light » selon le système (GNOME : préférence de style)."""
    hints = QGuiApplication.styleHints()
    return "dark" if hints.colorScheme() == Qt.ColorScheme.Dark else "light"


def colors(name: str | None = None) -> dict:
    return tokens()["color"][name or scheme()]


def stylesheet(name: str | None = None) -> str:
    c, t = colors(name), tokens()
    s, r = t["size"], t["radius"]
    return f"""
QMainWindow, QDialog {{ background: {c['bg']}; color: {c['text']}; }}
QWidget {{ font-size: {t['type']['base']['size']}px; }}
QToolBar {{ background: {c['surface']}; border: none; border-bottom: 1px solid {c['border']};
            min-height: {s['toolbar-height']}px; spacing: 4px; padding: 0 8px; }}
QToolButton#tool, QToolButton#favorite {{ min-width: {s['tool-button']}px; min-height: {s['tool-button']}px;
            border-radius: {r['md']}px; border: 2px solid transparent; color: {c['text']}; }}
QToolButton#tool:hover, QToolButton#favorite:hover {{ background: {c['accent-soft']}; }}
QToolButton#tool:checked, QToolButton#favorite:checked {{ background: {c['accent-soft']}; border-color: {c['accent']}; }}
QToolButton#tool:focus {{ border-color: {c['accent']}; }}
QToolButton#tool:disabled {{ color: {c['text-muted']}; }}
QFrame#popover {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: {r['lg']}px; }}
QMenuBar, QMenu {{ background: {c['surface']}; color: {c['text']}; }}
QMenu::item:selected, QMenuBar::item:selected {{ background: {c['accent-soft']}; }}
QLabel#muted {{ color: {c['text-muted']}; }}
QStatusBar {{ background: {c['surface']}; color: {c['text-muted']}; border-top: 1px solid {c['border']}; }}
QLineEdit, QSpinBox {{ background: {c['surface']}; color: {c['text']}; border: 1px solid {c['border-input']};
            border-radius: {r['sm']}px; padding: 4px 8px; min-height: {s['touch-min'] - 12}px; }}
QLineEdit:focus {{ border: 2px solid {c['accent']}; }}
QPushButton {{ background: {c['surface']}; color: {c['text']}; border: 1px solid {c['border-input']};
            border-radius: {r['md']}px; padding: 6px 16px; min-height: {s['touch-min'] - 12}px; }}
QPushButton:default {{ background: {c['accent']}; color: {c['on-accent']}; border-color: {c['accent']}; }}
QPushButton:focus {{ border: 2px solid {c['accent']}; }}
QPushButton:hover {{ background: {c['accent-soft']}; }}
QPushButton:checked {{ background: {c['accent-soft']}; border: 2px solid {c['accent']}; }}
QListWidget, QTreeView {{ background: {c['surface']}; color: {c['text']}; border: 1px solid {c['border']};
            border-radius: {r['md']}px; outline: none; }}
QListWidget::item, QTreeView::item {{ padding: 4px; border-radius: {r['sm']}px; }}
QListWidget::item:selected, QTreeView::item:selected {{ background: {c['accent-soft']}; color: {c['text']}; }}
QListWidget::item:hover, QTreeView::item:hover {{ background: {c['bg']}; }}
QDockWidget {{ color: {c['text-muted']}; font-weight: 600; }}
QDockWidget::title {{ background: {c['bg']}; padding: 6px 10px; }}
QTabBar::tab {{ background: {c['bg']}; color: {c['text-muted']}; padding: 6px 14px; border: none;
            border-bottom: 2px solid transparent; }}
QTabBar::tab:selected {{ color: {c['text']}; border-bottom: 2px solid {c['accent']}; background: {c['surface']}; }}
QComboBox, QSpinBox {{ background: {c['surface']}; color: {c['text']}; border: 1px solid {c['border-input']};
            border-radius: {r['sm']}px; padding: 4px 8px; min-height: {s['touch-min'] - 12}px; }}
QToolButton {{ color: {c['text']}; }}
QToolTip {{ background: {c['text']}; color: {c['surface']}; border: none; padding: 4px 8px; }}
"""


def apply(app) -> None:
    """Applique le style et le réapplique quand le thème système change."""
    app.setStyleSheet(stylesheet())
    app.styleHints().colorSchemeChanged.connect(lambda *_: app.setStyleSheet(stylesheet()))
