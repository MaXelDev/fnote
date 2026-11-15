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
from ...model.history import AddElements, Group, RemoveElements, ReplaceElements
from .base import Tool

HANDLE = 9.0          # demi-taille des poignées dessinées (px)
HANDLE_HIT = 24.0     # rayon de prise des poignées : assez large pour un doigt
ROTATE_GAP = 36.0     # distance de la poignée de rotation au-dessus du cadre (px)
SELECTION_PAD = 16.0  # marge du cadre autour des objets (px)
TAP_PX = 6.0          # un « lasso » plus petit que ça est un appui : on sélectionne l'objet touché
SNAP_DEG, SNAP_TOL = 15.0, 3.0
ACCENT = QColor("#26686c")

CLIPBOARD: dict = {"elements": [], "assets": {}}  # presse-papiers interne, partagé entre onglets
MIME_MARK = "application/x-fnote-selection"


class SelectionBar(QFrame):
    """Barre d'actions flottante au-dessus de la sélection (cibles larges pour le doigt)."""

    def __init__(self, tool: "LassoTool"):
        super().__init__(tool.canvas.viewport())
        self.tool = tool
        self.setObjectName("selectionBar")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(4)
        self.buttons = {}
        for key, label, tip in (("color", "Couleur", "Changer la couleur"), ("thinner", "−", "Plus fin"),
                                ("thicker", "+", "Plus épais"), ("crop", "Recadrer", "Recadrer l'image"),
                                ("copy", "Copier", "Copier (Ctrl+C)"), ("cut", "Couper", "Couper (Ctrl+X)"),
                                ("duplicate", "Dupliquer", "Dupliquer (Ctrl+D)"),
                                ("delete", "Supprimer", "Supprimer (Suppr)"), ("more", "⋯", "Plus d'actions")):
            b = QToolButton()
            b.setText(label)
            b.setToolTip(tip)
            b.setAccessibleName(tip)
            b.setMinimumSize(48, 48)
            b.clicked.connect(lambda _=False, k=key: self.tool.action(k))
            lay.addWidget(b)
            self.buttons[key] = b
        self.hide()

    def refresh(self):
        sel = self.tool.selection
        has_ink = any(isinstance(e, (Stroke, Shape)) for e in sel)
        for k in ("color", "thinner", "thicker"):
            self.buttons[k].setVisible(has_ink)
        self.buttons["crop"].setVisible(len(sel) == 1 and isinstance(sel[0], ImageItem))
        self.adjustSize()


def image_at(page, x: float, y: float):
    """Image la plus haute sous le point (en tenant compte de sa rotation), ou None."""
    for item in reversed(page.images):
        ix, iy, w, h = item.rect
        cx, cy = ix + w / 2, iy + h / 2
        a = math.radians(-item.rotation)  # point ramené dans le repère de l'image
        lx = cx + (x - cx) * math.cos(a) - (y - cy) * math.sin(a)
        ly = cy + (x - cx) * math.sin(a) + (y - cy) * math.cos(a)
        if ix <= lx <= ix + w and iy <= ly <= iy + h:
            return item
    return None


def element_at(page, x: float, y: float, tol: float):
    """Objet le plus haut sous le point (traits et formes d'abord, puis images), ou None."""
    from .eraser import hits
    found = hits(page, (x, y), (x, y), tol, False)
    return found[-1] if found else image_at(page, x, y)


class LassoTool(Tool):
    name = "lasso"
    long_press_menu = True  # appui long immobile : menu Coller / Insérer…
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
        self.return_mode: str | None = None  # outil à reprendre quand la sélection (par appui) se termine
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

    def _side_handles(self) -> list[QPointF]:
        c = self._corners_view()
        return [(c[i] + c[(i + 1) % 4]) / 2 for i in range(4)]  # haut, droite, bas, gauche

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
        # La poignée la plus proche gagne : avec de grandes zones de prise, elles se chevauchent.
        handles = [("rotate", self._rotate_handle())]
        handles += [(f"corner{i}", c) for i, c in enumerate(self._corners_view())]
        handles += [(f"side{i}", c) for i, c in enumerate(self._side_handles())]
        name, d = min(((n, _dist(pos, q)) for n, q in handles), key=lambda t: t[1])
        inside = QPolygonF(self._corners_view()).containsPoint(pos, Qt.FillRule.OddEvenFill)
        # Dedans, seule une prise précise vise une poignée ; dehors, la zone large (doigt) suffit.
        if d <= (HANDLE + 4 if inside else HANDLE_HIT):
            return name
        return "move" if inside else None

    # ----- geste -----
    def press(self, pos, pressure, t):
        hit = self._hit(pos)
        if hit:
            _, pt = self.canvas.view_to_page(pos, self.page_index)
            self._drag = {"kind": hit, "start": np.array([pt.x(), pt.y()])}
            self.bar.hide()
            return
        if self.return_mode is not None and self.selection:
            self._finish_tap_selection()
            return
        self.clear()
        self.page_index, _ = self.canvas.view_to_page(pos)
        self.path = [QPointF(pos)]

    def move(self, pos, pressure, t):
        if self.path:
            if self.rect_mode:
                self.path = [self.path[0], QPointF(pos)]
            else:
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
        if kind.startswith("side"):  # poignée de côté : étire dans un seul sens
            i = int(kind[-1])
            if i in (0, 2):
                ay = y1 if i == 0 else y0
                sy = (cur[1] - ay) / ((start[1] - ay) or 1e-9)
                return tf.scale_about(cx, ay, 1.0, math.copysign(max(abs(sy), 0.05), sy))
            ax = x0 if i == 1 else x1
            sx = (cur[0] - ax) / ((start[0] - ax) or 1e-9)
            return tf.scale_about(ax, cy, math.copysign(max(abs(sx), 0.05), sx), 1.0)
        corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        i = int(kind[-1])
        ax, ay = corners[(i + 2) % 4]  # coin opposé fixe ; les coins gardent les proportions
        sx = (cur[0] - ax) / ((start[0] - ax) or 1e-9)
        sy = (cur[1] - ay) / ((start[1] - ay) or 1e-9)
        s = max(abs(sx), abs(sy))
        sx, sy = math.copysign(s, sx), math.copysign(s, sy)
        sx = math.copysign(max(abs(sx), 0.05), sx)
        sy = math.copysign(max(abs(sy), 0.05), sy)
        return tf.scale_about(ax, ay, sx, sy)

    def release(self, pos, pressure, t):
        if self.path:
            path, self.path = self.path, []
            page = self.canvas.doc.pages[self.page_index]
            box = QPolygonF(path).boundingRect()
            if box.width() < TAP_PX and box.height() < TAP_PX:  # simple appui : l'objet touché
                _, pt = self.canvas.view_to_page(path[0], self.page_index)
                hit = element_at(page, pt.x(), pt.y(), 6 / self.canvas.zoom)
                self.select([hit] if hit is not None else [], self.page_index)
                self.canvas.viewport().update()
                return
            if self.rect_mode:
                a, b = path[0], path[-1]
                path = [a, QPointF(b.x(), a.y()), b, QPointF(a.x(), b.y())]
            poly = [self.canvas.view_to_page(p, self.page_index)[1] for p in path]
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

    @property
    def rect_mode(self) -> bool:
        return self.canvas.config.lasso_mode == "rect"

    def _finish_tap_selection(self):
        """Sélection ouverte en touchant un objet : un appui ailleurs la ferme et rend l'outil d'avant."""
        mode, self.return_mode = self.return_mode, None
        self.clear()
        if self.state is not None:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self.state.set_mode(mode))

    def dispose(self):
        self.return_mode = None
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
        pad = SELECTION_PAD / self.canvas.zoom  # cadre un peu plus large que les objets : on l'attrape mieux
        x0, y0, x1, y1 = tf.bounds(self.selection)
        self.box = (x0 - pad, y0 - pad, x1 + pad, y1 + pad)
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
        c = self._corners_view() + [self._rotate_handle()]
        top, bottom = min(p.y() for p in c), max(p.y() for p in c)
        left = min(p.x() for p in c)
        vp = self.canvas.viewport()
        x = int(min(max(4, left), vp.width() - self.bar.width() - 4))
        y = int(top - self.bar.height() - 16)  # au-dessus, hors de la main qui tient le stylet
        if y < 4:
            y = int(bottom + 16)
        y = min(y, vp.height() - self.bar.height() - 4)
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
        elif key == "more":
            self._more_menu()
        elif key in ("front", "back"):
            sel = self.selection
            self.canvas.hidden_ids = {e.id for e in sel}
            self.canvas.apply(Group([RemoveElements(page.id, sel), AddElements(page.id, sel, at_back=key == "back")]))
            self.select(sel, self.page_index)
        elif key == "save_image":
            self._save_image()

    def _more_menu(self):
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self.bar)
        for key, label in (("front", "Mettre au premier plan"), ("back", "Mettre à l'arrière-plan"),
                           ("save_image", "Enregistrer en image…")):
            menu.addAction(label, lambda k=key: self.action(k))
        b = self.bar.buttons["more"]
        menu.exec(b.mapToGlobal(b.rect().bottomLeft()))

    def _save_image(self):
        from PySide6.QtWidgets import QFileDialog
        if self._sprite is None:
            return
        path, _ = QFileDialog.getSaveFileName(self.canvas.window(), "Enregistrer la sélection en image",
                                              "selection.png", "Image PNG (*.png)")
        if path:
            self._sprite.save(path if path.lower().endswith(".png") else path + ".png", "PNG")

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
        # Presse-papiers système : marqueur FNote + image PNG pour les autres applis.
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
            pts = self.path
            if self.rect_mode and len(pts) == 2:
                a, b = pts
                pts = [a, QPointF(b.x(), a.y()), b, QPointF(a.x(), b.y()), a]
            path = QPainterPath(pts[0])
            for q in pts[1:]:
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
            p.drawEllipse(q, HANDLE, HANDLE)
        for q in self._side_handles():
            p.drawRoundedRect(QRectF(q.x() - HANDLE, q.y() - HANDLE / 2, 2 * HANDLE, HANDLE), 3, 3)
        rh = self._rotate_handle()
        p.drawLine((c[0] + c[1]) / 2, rh)
        p.drawEllipse(rh, HANDLE + 1, HANDLE + 1)
        if self._drag and self._drag["kind"] == "rotate":
            p.setPen(QColor("#15181d"))
            p.drawText(rh + QPointF(14, -8), f"{getattr(self, 'angle', 0.0):.0f}°")


def _dist(a: QPointF, b: QPointF) -> float:
    return math.hypot(a.x() - b.x(), a.y() - b.y())


def paste(canvas, tool: "LassoTool | None" = None, at_view: QPointF | None = None):
    """Colle le presse-papiers interne et le sélectionne : à at_view (coin haut gauche),
    sinon sur la page courante, décalé de l'original."""
    if not CLIPBOARD["elements"]:
        return False
    for name, data in CLIPBOARD["assets"].items():
        canvas.doc.assets.setdefault(name, data)
    if at_view is not None:
        index, pt = canvas.view_to_page(at_view)
        x0, y0, _, _ = tf.bounds(CLIPBOARD["elements"])
        dx, dy = pt.x() - x0, pt.y() - y0
    else:
        index, dx, dy = canvas.current_page(), 16, 16
    copies = [tf.with_new_id(e, dx, dy) for e in CLIPBOARD["elements"]]
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
