"""Palette de couleurs : préréglages, couleurs personnalisées, récentes, sélecteur avancé.

Le sélecteur avancé est la boîte de couleur de Qt (carré HSV, champs RGB et HEX,
opacité), en version non native pour avoir tous les champs sous GNOME.
"""
from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QAbstractButton, QColorDialog, QGridLayout, QLabel, QVBoxLayout, QWidget)

from ..model import colors
from . import style

COLUMNS = 8
MAX_CUSTOM = 16


class Swatch(QAbstractButton):
    def __init__(self, color: str | None, parent=None, plus: bool = False):
        super().__init__(parent)
        self.color, self.plus = color, plus
        self.setCheckable(not plus)
        size = style.tokens()["size"]["swatch"]
        self.setFixedSize(QSize(size, size))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Autre couleur…" if plus else colors.rgb(color))
        self.setAccessibleName(self.toolTip())

    def paintEvent(self, _):
        c = style.colors()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(4, 4, -4, -4)
        if self.plus:
            p.setPen(QPen(QColor(c["border-input"]), 1.5))
            p.drawEllipse(r)
            m = r.center()
            p.drawLine(m.x() - 6, m.y(), m.x() + 6, m.y())
            p.drawLine(m.x(), m.y() - 6, m.x(), m.y() + 6)
            return
        p.setPen(QPen(QColor(c["border"]), 1))
        p.setBrush(QColor(colors.rgb(self.color)))
        p.drawEllipse(r)
        if self.isChecked() or self.hasFocus():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(c["text"]), 2))
            p.drawEllipse(QRectF(self.rect()).adjusted(1, 1, -1, -1))


class ColorPalette(QWidget):
    """Émet colorPicked("#rrggbbaa") ; alpha force l'opacité (surligneur)."""

    colorPicked = Signal(str)

    def __init__(self, config, presets: list[str], current: str, alpha: int | None = None, parent=None):
        super().__init__(parent)
        self.config, self.presets, self.alpha = config, presets, alpha
        self.current = current
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._build()

    def _section(self, title: str, values: list[str], plus: bool = False):
        if not values and not plus:
            return
        if title:
            lab = QLabel(title)
            lab.setObjectName("muted")
            self._lay.addWidget(lab)
        grid = QGridLayout()
        grid.setSpacing(2)
        items = [(v, False) for v in values] + ([(None, True)] if plus else [])
        for k, (v, is_plus) in enumerate(items):
            b = Swatch(v, self, plus=is_plus)
            if is_plus:
                b.clicked.connect(self._advanced)
            else:
                b.setChecked(colors.rgb(v) == colors.rgb(self.current))
                b.clicked.connect(lambda _=False, v=v: self._pick(v))
            grid.addWidget(b, k // COLUMNS, k % COLUMNS)
        self._lay.addLayout(grid)

    def _build(self):
        while self._lay.count():
            item = self._lay.takeAt(0)
            if w := item.widget():
                w.deleteLater()
            elif lay := item.layout():
                while lay.count():
                    if w := lay.takeAt(0).widget():
                        w.deleteLater()
        self._section("", self.presets)
        self._section("Mes couleurs", self.config.custom_colors, plus=True)
        self._section("Récentes", self.config.recent_colors)

    def _pick(self, value: str):
        c = colors.normalize(value, self.alpha)
        if c is None:
            return
        self.current = c
        self.config.recent_colors = colors.push_recent(self.config.recent_colors, c)
        self.colorPicked.emit(c)
        self._build()

    def _advanced(self):
        initial = QColor(colors.rgb(self.current))
        initial.setAlpha(int(self.current[7:9], 16) if len(self.current) == 9 else 255)
        dlg = QColorDialog(initial, self.window())
        dlg.setWindowTitle("Choisir une couleur")
        dlg.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog)
        if self.alpha is None:
            dlg.setOption(QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if dlg.exec() != QColorDialog.DialogCode.Accepted:
            return
        q = dlg.selectedColor()
        value = colors.normalize(q.name(QColor.NameFormat.HexRgb), self.alpha if self.alpha is not None else q.alpha())
        custom = [x for x in self.config.custom_colors if colors.rgb(x) != colors.rgb(value)]
        self.config.custom_colors = ([value] + custom)[:MAX_CUSTOM]
        self._pick(value)
