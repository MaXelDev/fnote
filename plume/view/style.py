"""Feuille de style Qt (QSS) centralisée, générée depuis resources/tokens.json."""
from __future__ import annotations

import json
from functools import cache
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

TOKENS_PATH = Path(__file__).resolve().parent.parent / "resources" / "tokens.json"
CLOSE_ICON = (TOKENS_PATH.parent / "close.svg").as_posix()


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
QFrame#popover, QFrame#selectionBar {{ background: {c['surface']}; border: 1px solid {c['border']};
            border-radius: {r['lg']}px; }}
QFrame#selectionBar QToolButton {{ min-width: {s['touch-min']}px; min-height: {s['touch-min']}px; padding: 0 10px;
            border-radius: {r['md']}px; }}
QFrame#selectionBar QToolButton:hover, QFrame#selectionBar QToolButton:pressed {{ background: {c['accent-soft']}; }}
QMenuBar, QMenu {{ background: {c['surface']}; color: {c['text']}; }}
QMenu {{ border: 1px solid {c['border']}; border-radius: {r['md']}px; padding: 6px; }}
QMenu::item {{ min-height: {s['menu-item'] - 24}px; padding: 12px 28px 12px 16px; border-radius: {r['sm']}px; }}
QMenu::separator {{ height: 1px; background: {c['border']}; margin: 6px 10px; }}
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
QListWidget::item, QTreeView::item {{ padding: 8px 4px; min-height: {s['touch-min'] - 16}px;
            border-radius: {r['sm']}px; }}
QListWidget::item:selected, QTreeView::item:selected {{ background: {c['accent-soft']}; color: {c['text']}; }}
QListWidget::item:hover, QTreeView::item:hover {{ background: {c['bg']}; }}
QDockWidget {{ color: {c['text-muted']}; font-weight: 600; }}
QDockWidget::title {{ background: {c['bg']}; padding: 12px 10px; }}
QTabBar::tab {{ background: {c['bg']}; color: {c['text-muted']}; padding: 12px 18px; border: none;
            border-bottom: 2px solid transparent; }}
QTabBar::tab:selected {{ color: {c['text']}; border-bottom: 2px solid {c['accent']}; background: {c['surface']}; }}
QComboBox, QSpinBox {{ background: {c['surface']}; color: {c['text']}; border: 1px solid {c['border-input']};
            border-radius: {r['sm']}px; padding: 4px 8px; min-height: {s['touch-min'] - 12}px; }}
QToolButton {{ color: {c['text']}; }}
QCheckBox {{ spacing: 10px; min-height: {s['touch-min']}px; }}
QCheckBox::indicator {{ width: {s['indicator']}px; height: {s['indicator']}px; }}
QSlider {{ min-height: {s['touch-min']}px; }}
QSlider::groove:horizontal {{ height: 6px; background: {c['border']}; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {c['accent']}; border-radius: 3px; }}
QSlider::handle:horizontal {{ width: {s['slider-handle']}px; height: {s['slider-handle']}px;
            margin: -{(s['slider-handle'] - 6) // 2}px 0; border-radius: {s['slider-handle'] // 2}px;
            background: {c['surface']}; border: 2px solid {c['accent']}; }}
QScrollBar:vertical {{ width: {s['scrollbar']}px; background: transparent; }}
QScrollBar:horizontal {{ height: {s['scrollbar']}px; background: transparent; }}
QScrollBar::handle {{ background: {c['border-input']}; border-radius: {s['scrollbar'] // 2}px;
            min-height: {s['touch-min']}px; min-width: {s['touch-min']}px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QTabBar::close-button {{ image: url({CLOSE_ICON}); subcontrol-position: right; width: 32px; height: 32px;
            border-radius: {r['sm']}px; }}
QTabBar::close-button:hover {{ background: {c['accent-soft']}; }}
QDockWidget {{ titlebar-close-icon: url({CLOSE_ICON}); }}
QDockWidget::close-button {{ width: 32px; height: 32px; border-radius: {r['sm']}px; }}
QDockWidget::close-button:hover {{ background: {c['accent-soft']}; }}
QComboBox QAbstractItemView::item {{ min-height: {s['touch-min']}px; }}
QSpinBox::up-button, QSpinBox::down-button {{ width: 28px; }}
QToolTip {{ background: {c['text']}; color: {c['surface']}; border: none; padding: 4px 8px; }}
"""


def apply(app) -> None:
    """Applique le style et le réapplique quand le thème système change."""
    app.setStyleSheet(stylesheet())
    app.styleHints().colorSchemeChanged.connect(lambda *_: app.setStyleSheet(stylesheet()))
