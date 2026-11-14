"""Lasso : sélection libre, déplacer, redimensionner (proportions), pivoter, actions.

Pendant une manipulation, la sélection est masquée de la page et dessinée comme une
image transformée dans l'overlay (aucun recalcul de page par mouvement). Au lâcher,
une seule commande d'historique remplace les éléments par leurs versions transformées.
"""
from __future__ import annotations

import math
from dataclasses import replace

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QPolygonF, QTransform
from PySide6.QtWidgets import QFrame, QHBoxLayout, QToolButton

from ...engine import transform as tf
from ...model import colors
from ...model.elements import ImageItem, Shape, Stroke
from ...model.history import AddElements, RemoveElements, ReplaceElements
from .base import Tool

HANDLE = 7.0          # demi-taille des poignées (px)
ROTATE_GAP = 30.0     # distance de la poignée de rotation au-dessus du cadre (px)
SNAP_DEG, SNAP_TOL = 15.0, 3.0
ACCENT = QColor("#26686c")

CLIPBOARD: dict = {"elements": [], "assets": {}}  # presse-papiers interne, partagé entre onglets
MIME_MARK = "application/x-plume-selection"


class SelectionBar(QFrame):
    """Barre flottante sous la sélection."""

    def __init__(self, tool: "LassoTool"):
        super().__init__(tool.canvas.viewport())
        self.tool = tool
        self.setObjectName("popover")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(2)
        self.buttons = {}
        for key, label, tip in (("color", "Couleur", "Changer la couleur"), ("thinner", "−", "Plus fin"),
                                ("thicker", "+", "Plus épais"), ("ratio", "Proportions", "Conserver les proportions"),
                                ("crop", "Recadrer", "Recadrer l'image"), ("duplicate", "Dupliquer", "Dupliquer"),
                                ("copy", "Copier", "Copier (Ctrl+C)"), ("cut", "Couper", "Couper (Ctrl+X)"),
                                ("delete", "Supprimer", "Supprimer (Suppr)")):
            b = QToolButton()
            b.setText(label)
            b.setToolTip(tip)
            b.setMinimumHeight(36)
            b.clicked.connect(lambda _=False, k=key: self.tool.action(k))
            lay.addWidget(b)
            self.buttons[key] = b
        self.buttons["ratio"].setCheckable(True)
        self.buttons["ratio"].setChecked(True)
        self.hide()

    def refresh(self):
        sel = self.tool.selection
        has_ink = any(isinstance(e, (Stroke, Shape)) for e in sel)
        for k in ("color", "thinner", "thicker"):
            self.buttons[k].setVisible(has_ink)
        self.buttons["crop"].setVisible(len(sel) == 1 and isinstance(sel[0], ImageItem))
        self.adjustSize()


class LassoTool(Tool):
    name = "lasso"
    dot_color = ACCENT

    def __init__(self, canvas, state=None):
        super().__init__(canvas)
        self.state = state
        self.path: list[QPointF] = []
        self.selection: list = []
        self.page_index = -1
        self.box = (0.0, 0.0, 0.0, 0.0)     # cadre de la sélection, coordonnées de page
        self.m = np.eye(3)                   # transformation en cours (aperçu)
        self._drag: dict | None = None
        self._sprite: QImage | None = None
        self.bar = SelectionBar(self)

    @property
    def busy(self) -> bool:
        return bool(self.path) or self._drag is not None

    # ----- géométrie écran -----
    def _view_transform(self) -> QTransform:
        r = self.canvas.page_rect(self.page_index)
        z = self.canvas.zoom
        m = self.m
        qm = QTransform(m[0, 0], m[1, 0], m[0, 1], m[1, 1], m[0, 2], m[1, 2])
        return qm * QTransform(z, 0, 0, z, r.x(), r.y())

    def _corners_view(self) -> list[QPointF]:
        x0, y0, x1, y1 = self.box
        t = self._view_transform()
        return [t.map(QPointF(x, y)) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]

    def _rotate_handle(self) -> QPointF:
        c = self._corners_view()
        top_mid = (c[0] + c[1]) / 2
        center = (c[0] + c[2]) / 2
        d = top_mid - center
        n = math.hypot(d.x(), d.y()) or 1
        return top_mid + d / n * ROTATE_GAP

    def _hit(self, pos: QPointF) -> str | None:
        if not self.selection:
            return None
        if _dist(pos, self._rotate_handle()) <= HANDLE * 1.8:
            return "rotate"
        for i, c in enumerate(self._corners_view()):
            if _dist(pos, c) <= HANDLE * 1.8:
                return f"corner{i}"
        if QPolygonF(self._corners_view()).containsPoint(pos, Qt.FillRule.OddEvenFill):
            return "move"
        return None

    # ----- geste -----
    def press(self, pos, pressure, t):
        hit = self._hit(pos)
        if hit:
            _, pt = self.canvas.view_to_page(pos, self.page_index)
            self._drag = {"kind": hit, "start": np.array([pt.x(), pt.y()])}
            self.bar.hide()
            return
        self.clear()
        self.page_index, _ = self.canvas.view_to_page(pos)
        self.path = [QPointF(pos)]

    def move(self, pos, pressure, t):
        if self.path:
            self.path.append(QPointF(pos))
            self.canvas.viewport().update()
            return
        if self._drag is None:
            return
        _, pt = self.canvas.view_to_page(pos, self.page_index)
        cur = np.array([pt.x(), pt.y()])
        self.m = self._drag_matrix(self._drag, cur)
        self.canvas.viewport().update()

    def _drag_matrix(self, drag, cur) -> np.ndarray:
        x0, y0, x1, y1 = self.box
        start = drag["start"]
        kind = drag["kind"]
        if kind == "move":
            d = cur - start
            return tf.translate(*d)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if kind == "rotate":
            a = math.degrees(math.atan2(cur[1] - cy, cur[0] - cx) - math.atan2(start[1] - cy, start[0] - cx))
            snapped = round(a / SNAP_DEG) * SNAP_DEG
            if abs(a - snapped) < SNAP_TOL:
                a = snapped
            self.angle = a
            return tf.rotate_about(cx, cy, a)
        corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        i = int(kind[-1])
        ax, ay = corners[(i + 2) % 4]  # coin opposé fixe
        sx = (cur[0] - ax) / ((start[0] - ax) or 1e-9)
        sy = (cur[1] - ay) / ((start[1] - ay) or 1e-9)
        if self.bar.buttons["ratio"].isChecked():
            s = max(abs(sx), abs(sy))
            sx, sy = math.copysign(s, sx), math.copysign(s, sy)
        sx = math.copysign(max(abs(sx), 0.05), sx)
        sy = math.copysign(max(abs(sy), 0.05), sy)
        return tf.scale_about(ax, ay, sx, sy)

    def release(self, pos, pressure, t):
        if self.path:
            poly = [self.canvas.view_to_page(p, self.page_index)[1] for p in self.path]
            self.path = []
            page = self.canvas.doc.pages[self.page_index]
            self.select(tf.select_in_lasso(page, [(p.x(), p.y()) for p in poly]), self.page_index)
            self.canvas.viewport().update()
            return
        if self._drag is not None:
            self._drag = None
            if not np.allclose(self.m, np.eye(3)):
                new = [tf.transform_element(e, self.m) for e in self.selection]
                self._replace(new)
            self.m = np.eye(3)
            self._show_bar()

    def dispose(self):
        self.clear()
        self.bar.deleteLater()

    def cancel(self):
        self.path = []
        self._drag = None
        self.m = np.eye(3)
        self.canvas.viewport().update()

    # ----- sélection -----
    def select(self, elements: list, page_index: int):
        self.selection = list(elements)
        self.page_index = page_index
        if not self.selection:
            self.clear()
            return
        self.box = tf.bounds(self.selection)
        self.m = np.eye(3)
        page_id = self.canvas.doc.pages[page_index].id
        self.canvas.hidden_ids = {e.id for e in self.selection}
        self.canvas.invalidate({page_id})
        self._render_sprite()
        self._show_bar()

    def clear(self):
        if self.selection:
            ids = {self.canvas.doc.pages[self.page_index].id} if self.page_index < len(self.canvas.doc.pages) else None
            self.selection = []
            self.canvas.hidden_ids = set()
            self.canvas.invalidate(ids)
        self._sprite = None
        self.bar.hide()
        self.canvas.viewport().update()

    def _render_sprite(self):
        x0, y0, x1, y1 = self.box
        z = self.canvas.zoom * self.canvas.viewport().devicePixelRatioF()
        w, h = max(1, int((x1 - x0) * z) + 2), max(1, int((y1 - y0) * z) + 2)
        img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(z, z)
        p.translate(-x0, -y0)
        for e in self.selection:
            self.canvas.renderer.paint_element(p, e)
        p.end()
        self._sprite = img

    def _show_bar(self):
        if not self.selection:
            return
        self.bar.refresh()
        c = self._corners_view()
        bottom = max(p.y() for p in c)
        left = min(p.x() for p in c)
        vp = self.canvas.viewport()
        x = int(min(max(4, left), vp.width() - self.bar.width() - 4))
        y = int(bottom + 12)
        if y + self.bar.height() > vp.height() - 4:
            y = int(min(p.y() for p in c) - self.bar.height() - 12)
        self.bar.move(x, max(4, y))
        self.bar.show()
        self.bar.raise_()

    def _replace(self, new: list):
        page = self.canvas.doc.pages[self.page_index]
        self.canvas.hidden_ids = {e.id for e in new}
        self.canvas.apply(ReplaceElements(page.id, self.selection, new))
        self.select(new, self.page_index)

    # ----- actions -----
    def action(self, key: str):
        if not self.selection:
            return
        page = self.canvas.doc.pages[self.page_index]
        if key == "delete":
            sel = self.selection
            self.clear()
            self.canvas.apply(RemoveElements(page.id, sel))
        elif key == "copy":
            self.copy()
        elif key == "cut":
            self.copy()
            self.action("delete")
        elif key == "duplicate":
            copies = [tf.with_new_id(e, 12, 12) for e in self.selection]
            self.clear()
            self.canvas.apply(AddElements(page.id, copies))
            self.select(copies, self.page_index)
        elif key in ("thinner", "thicker"):
            f = 0.8 if key == "thinner" else 1.25
            self._replace([replace(e, width=max(0.2, e.width * f)) if isinstance(e, (Stroke, Shape)) else e
                           for e in self.selection])
        elif key == "color":
            self._pick_color()
        elif key == "crop":
            self._crop()

    def recolor(self, value: str):
        def paint(e):
            if isinstance(e, Stroke) and e.is_highlight:
                return replace(e, color=colors.normalize(value, colors.HIGHLIGHTER_ALPHA))
            if isinstance(e, (Stroke, Shape)):
                return replace(e, color=colors.normalize(value))
            return e
        self._replace([paint(e) for e in self.selection])

    def _pick_color(self):
        from ...view.color_picker import ColorPalette
        from ...view.popovers import Popover
        pop = Popover("Couleur de la sélection")
        first = next(e for e in self.selection if isinstance(e, (Stroke, Shape)))
        pal = ColorPalette(self.canvas.config, colors.INK_PALETTE, first.color)
        pal.colorPicked.connect(lambda c: (self.recolor(c), pop.close()))
        pop.lay.addWidget(pal)
        self._popover = pop
        pop.show_below(self.bar.buttons["color"])

    def _crop(self):
        from ...view.crop_dialog import ask_crop, combine_crop
        item = self.selection[0]
        img = self.canvas.renderer.image(item.asset)
        x0, y0, x1, y1 = item.crop
        visible = img.copy(int(x0 * img.width()), int(y0 * img.height()),
                           max(1, int((x1 - x0) * img.width())), max(1, int((y1 - y0) * img.height())))
        sub = ask_crop(self.canvas.window(), visible)
        if sub is None:
            return
        x, y, w, h = item.rect
        rect = (x + sub[0] * w, y + sub[1] * h, (sub[2] - sub[0]) * w, (sub[3] - sub[1]) * h)
        self._replace([replace(item, crop=combine_crop(item.crop, sub), rect=rect)])

    def copy(self):
        assets = {e.asset: self.canvas.doc.assets[e.asset] for e in self.selection
                  if isinstance(e, ImageItem) and e.asset in self.canvas.doc.assets}
        CLIPBOARD["elements"] = [replace(e) for e in self.selection]
        CLIPBOARD["assets"] = assets
        # Presse-papiers système : marqueur Plume + image PNG pour les autres applis.
        from PySide6.QtCore import QMimeData
        from PySide6.QtWidgets import QApplication
        mime = QMimeData()
        mime.setData(MIME_MARK, b"1")
        if self._sprite is not None:
            mime.setImageData(self._sprite)
        QApplication.clipboard().setMimeData(mime)

    # ----- dessin -----
    def paint_overlay(self, p: QPainter):
        if self.path:
            path = QPainterPath(self.path[0])
            for q in self.path[1:]:
                path.lineTo(q)
            p.setPen(QPen(ACCENT, 1.5, Qt.PenStyle.DashLine))
            p.setBrush(QColor(38, 104, 108, 25))
            p.drawPath(path)
            return
        if not self.selection or self.page_index >= len(self.canvas.doc.pages):
            return
        if self._sprite is not None:
            x0, y0, x1, y1 = self.box
            p.save()
            p.setTransform(self._view_transform(), True)
            p.drawImage(QRectF(x0, y0, self._sprite.width() / (self.canvas.zoom * self.canvas.viewport().devicePixelRatioF()),
                               self._sprite.height() / (self.canvas.zoom * self.canvas.viewport().devicePixelRatioF())),
                        self._sprite)
            p.restore()
        c = self._corners_view()
        p.setPen(QPen(ACCENT, 1.5, Qt.PenStyle.DashLine))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPolygon(QPolygonF(c))
        p.setPen(QPen(ACCENT, 1.5))
        p.setBrush(QColor("#ffffff"))
        for q in c:
            p.drawRect(QRectF(q.x() - HANDLE, q.y() - HANDLE, 2 * HANDLE, 2 * HANDLE))
        rh = self._rotate_handle()
        p.drawLine((c[0] + c[1]) / 2, rh)
        p.drawEllipse(rh, HANDLE + 1, HANDLE + 1)
        if self._drag and self._drag["kind"] == "rotate":
            p.setPen(QColor("#15181d"))
            p.drawText(rh + QPointF(14, -8), f"{getattr(self, 'angle', 0.0):.0f}°")


def _dist(a: QPointF, b: QPointF) -> float:
    return math.hypot(a.x() - b.x(), a.y() - b.y())


def paste(canvas, tool: "LassoTool | None" = None):
    """Colle le presse-papiers interne sur la page courante (décalé), et le sélectionne."""
    if not CLIPBOARD["elements"]:
        return False
    for name, data in CLIPBOARD["assets"].items():
        canvas.doc.assets.setdefault(name, data)
    index = canvas.current_page()
    copies = [tf.with_new_id(e, 16, 16) for e in CLIPBOARD["elements"]]
    canvas.apply(AddElements(canvas.doc.pages[index].id, copies))
    if tool is not None:
        tool.select(copies, index)
    return True


def release_clipboard_on_quit(app) -> None:
    """À la fermeture, remplace notre QMimeData par une simple image gérée par Qt.

    Sans ça, PySide détruit l'objet Python du presse-papiers après QApplication
    et le processus plante en quittant (vu en hors écran comme sous Wayland).
    """
    def swap():
        cb = app.clipboard()
        mime = cb.mimeData()
        if mime is not None and mime.hasFormat(MIME_MARK):
            img = cb.image()
            cb.clear()
            if not img.isNull():
                cb.setImage(img)
    app.aboutToQuit.connect(swap)
