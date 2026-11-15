"""Réglages des outils dans des popovers sous la barre (un geste pour y accéder)."""
from __future__ import annotations

import math

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QFrame, QHBoxLayout, QLabel, QPushButton, QSlider,
                               QVBoxLayout, QWidget)

from ..model import colors
from .color_picker import ColorPalette
from .render import qcolor

TIPS = [("fountain", "Plume"), ("ballpoint", "Bille"), ("pencil", "Crayon")]


class Popover(QFrame):
    def __init__(self, title: str):
        super().__init__(None, Qt.WindowType.Popup)
        self.setObjectName("popover")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(14, 12, 14, 14)
        self.lay.setSpacing(8)
        head = QLabel(title)
        head.setStyleSheet("font-weight: 600;")
        self.lay.addWidget(head)

    def show_below(self, widget: QWidget):
        self.adjustSize()
        pos = widget.mapToGlobal(QPoint(0, widget.height() + 4))
        self.move(pos)
        self.show()


def slider(minimum: int, maximum: int, value: int, on_change, fmt) -> QWidget:
    w = QWidget()
    row = QHBoxLayout(w)
    row.setContentsMargins(0, 0, 0, 0)
    s = QSlider(Qt.Orientation.Horizontal)
    s.setRange(minimum, maximum)
    s.setValue(value)
    s.setMinimumWidth(180)
    lab = QLabel(fmt(value))
    lab.setMinimumWidth(56)
    s.valueChanged.connect(lambda v: (lab.setText(fmt(v)), on_change(v)))
    row.addWidget(s)
    row.addWidget(lab)
    return w


class StrokePreview(QWidget):
    def __init__(self, spec_getter):
        super().__init__()
        self.spec_getter = spec_getter
        self.setFixedHeight(36)

    def paintEvent(self, _):
        spec = self.spec_getter()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), qcolor("#ffffffff"))
        w = self.width()
        steps = 40
        for i in range(steps):
            t = i / steps
            f = 0.35 + 0.65 * t if spec["tool"] == "fountain" else 1.0
            p.setPen(QPen(qcolor(spec["color"]), max(0.6, spec["width"] * 2 * f), Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.RoundCap))
            y0 = 18 + 8 * math.sin(t * 6.28)
            y1 = 18 + 8 * math.sin((i + 1) / steps * 6.28)
            p.drawLine(QPointF(10 + t * (w - 20), y0), QPointF(10 + (i + 1) / steps * (w - 20), y1))


class PenPopover(Popover):
    def __init__(self, state):
        super().__init__("Stylo")
        self.state = state
        tips = QHBoxLayout()
        group = QButtonGroup(self)
        for key, label in TIPS:
            b = QPushButton(label)
            b.setCheckable(True)
            b.setChecked(state.pen_spec["tool"] == key)
            b.clicked.connect(lambda _=False, k=key: self._set(tool=k))
            group.addButton(b)
            tips.addWidget(b)
        self.lay.addLayout(tips)
        self.preview = StrokePreview(lambda: self.state.pen_spec)
        self.lay.addWidget(self.preview)
        self.lay.addWidget(slider(3, 80, int(state.pen_spec["width"] * 10),
                                  lambda v: self._set(width=v / 10), lambda v: f"{v / 10:.1f} pt"))
        pal = ColorPalette(state.config, colors.INK_PALETTE, state.pen_spec["color"])
        pal.colorPicked.connect(lambda c: self._set(color=c))
        self.lay.addWidget(pal)

    def _set(self, **values):
        self.state.update_pen(**values)
        self.preview.update()


class HighlighterPopover(Popover):
    def __init__(self, state):
        super().__init__("Surligneur")
        self.state = state
        spec = state.config.highlighter
        pal = ColorPalette(state.config, colors.HIGHLIGHTER_PALETTE, spec["color"], alpha=colors.HIGHLIGHTER_ALPHA)
        pal.colorPicked.connect(lambda c: state.update_highlighter(color=c))
        self.lay.addWidget(pal)
        self.lay.addWidget(slider(4, 40, int(spec["width"]), lambda v: state.update_highlighter(width=float(v)),
                                  lambda v: f"{v} pt"))
        straight = QCheckBox("Surligneur droit (se redresse à l'horizontale)")
        straight.setChecked(state.config.straight_highlighter)
        straight.toggled.connect(self._straight)
        self.lay.addWidget(straight)

    def _straight(self, on: bool):
        self.state.config.straight_highlighter = on
        self.state.changed.emit()


class EraserPopover(Popover):
    def __init__(self, state):
        super().__init__("Gomme")
        self.state = state
        spec = state.config.eraser
        modes = QHBoxLayout()
        group = QButtonGroup(self)
        for key, label in (("stroke", "Trait entier"), ("partial", "Partielle")):
            b = QPushButton(label)
            b.setCheckable(True)
            b.setChecked(spec["mode"] == key)
            b.clicked.connect(lambda _=False, k=key: state.update_eraser(mode=k))
            group.addButton(b)
            modes.addWidget(b)
        self.lay.addLayout(modes)
        self.lay.addWidget(slider(4, 80, int(spec["size"]), lambda v: state.update_eraser(size=float(v)),
                                  lambda v: f"{v} pt"))
        only = QCheckBox("N'effacer que le surligneur")
        only.setChecked(spec.get("highlight_only", False))
        only.toggled.connect(lambda on: state.update_eraser(highlight_only=on))
        self.lay.addWidget(only)


class LassoPopover(Popover):
    def __init__(self, state):
        super().__init__("Sélection")
        self.state = state
        row = QHBoxLayout()
        group = QButtonGroup(self)
        for key, label in (("free", "Lasso libre"), ("rect", "Rectangle")):
            b = QPushButton(label)
            b.setCheckable(True)
            b.setChecked(state.config.lasso_mode == key)
            b.clicked.connect(lambda _=False, k=key: self._set(k))
            group.addButton(b)
            row.addWidget(b)
        self.lay.addLayout(row)
        hint = QLabel("Astuce : touche un objet ou une image pour le sélectionner directement.")
        hint.setWordWrap(True)
        self.lay.addWidget(hint)

    def _set(self, mode: str):
        self.state.config.lasso_mode = mode
        self.state.changed.emit()
