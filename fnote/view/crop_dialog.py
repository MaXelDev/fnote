"""Recadrage simple : on trace le rectangle à garder sur l'image."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QWidget

MAX_VIEW = 640


class CropArea(QWidget):
    def __init__(self, img: QImage):
        super().__init__()
        self.img = img.scaled(MAX_VIEW, MAX_VIEW, Qt.AspectRatioMode.KeepAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)
        self.setFixedSize(self.img.size())
        self.sel = QRectF(0, 0, self.img.width(), self.img.height())
        self._start: QPointF | None = None
        self.setAttribute(Qt.WidgetAttribute.WA_TabletTracking)

    def _clamp(self, p: QPointF) -> QPointF:
        return QPointF(min(max(p.x(), 0), self.width()), min(max(p.y(), 0), self.height()))

    def mousePressEvent(self, e):
        self._start = self._clamp(e.position())
        self.sel = QRectF(self._start, self._start)
        self.update()

    def mouseMoveEvent(self, e):
        if self._start is not None:
            self.sel = QRectF(self._start, self._clamp(e.position())).normalized()
            self.update()

    def mouseReleaseEvent(self, e):
        self._start = None
        if self.sel.width() < 4 or self.sel.height() < 4:
            self.sel = QRectF(0, 0, self.width(), self.height())
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.drawImage(0, 0, self.img)
        shade = QColor(0, 0, 0, 120)
        full = QRectF(self.rect())
        for r in (QRectF(0, 0, full.width(), self.sel.top()),
                  QRectF(0, self.sel.bottom(), full.width(), full.height() - self.sel.bottom()),
                  QRectF(0, self.sel.top(), self.sel.left(), self.sel.height()),
                  QRectF(self.sel.right(), self.sel.top(), full.width() - self.sel.right(), self.sel.height())):
            p.fillRect(r, shade)
        p.setPen(QPen(QColor("#ffffff"), 2, Qt.PenStyle.DashLine))
        p.drawRect(self.sel)

    def fractions(self) -> tuple[float, float, float, float]:
        w, h = self.width(), self.height()
        return (self.sel.left() / w, self.sel.top() / h, self.sel.right() / w, self.sel.bottom() / h)


def ask_crop(parent, img: QImage) -> tuple[float, float, float, float] | None:
    """Renvoie la zone gardée en fractions (x0, y0, x1, y1) de l'image affichée, ou None."""
    dlg = QDialog(parent)
    dlg.setWindowTitle("Recadrer l'image")
    lay = QVBoxLayout(dlg)
    hint = QLabel("Trace le rectangle à garder.")
    hint.setObjectName("muted")
    area = CropArea(img)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    for w in (hint, area, buttons):
        lay.addWidget(w)
    return area.fractions() if dlg.exec() == QDialog.DialogCode.Accepted else None


def combine_crop(old, sub):
    """Applique un recadrage `sub` (fractions de la zone visible) à un recadrage existant."""
    ox0, oy0, ox1, oy1 = old
    sx0, sy0, sx1, sy1 = sub
    w, h = ox1 - ox0, oy1 - oy0
    return (ox0 + sx0 * w, oy0 + sy0 * h, ox0 + sx1 * w, oy0 + sy1 * h)
