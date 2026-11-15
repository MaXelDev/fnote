"""Canevas multi-pages : défilement vertical continu, zoom, caches par page, entrées.

Règles de fluidité :
- les traits finis sont « cuits » dans une image par page, seule la page touchée change ;
- le trait en cours est peint dans un overlay et seul le dernier segment est rafraîchi ;
- seules les pages visibles sont peintes ; au zoom on affiche d'abord l'image mise à
  l'échelle, puis la version nette est recalculée page par page après le geste.
"""
from __future__ import annotations

import math
import time

from PySide6.QtCore import QEvent, QPointF, QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPointingDevice
from PySide6.QtWidgets import QAbstractScrollArea

from ..controller.input_router import router
from ..engine.pressure import PressureCurve
from ..model.document import Page, next_background
from ..model.history import AddElements, AddPage, Command, History
from . import style
from .render import PageRenderer
from .ruler import Ruler

MARGIN = 18.0   # points autour du contenu
GAP = 14.0      # points entre deux pages
MIN_ZOOM, MAX_ZOOM = 0.2, 6.0
SHARP_DELAY_MS = 140
CACHE_KEEP = 3  # pages gardées en cache de part et d'autre de la zone visible

_ERASER_POINTER = QPointingDevice.PointerType.Eraser
TAP_S, TAP_MOVE_PX = 0.35, 8.0  # appui bref : durée max (s) et déplacement max (px)
LONG_PRESS_MS = 1000  # appui long immobile : menu contextuel


class Canvas(QAbstractScrollArea):
    changed = Signal()          # le document a été modifié
    zoomChanged = Signal(float)
    pageChanged = Signal(int)
    toolFinished = Signal()     # un geste vient de se terminer
    imageTapped = Signal(int, object)  # appui bref sur une image (page, ImageItem) : à sélectionner
    longPressed = Signal(int, object, QPointF)  # appui long : (page, élément touché ou None, position vue)
    pagesInvalidated = Signal(object)  # ensemble d'id de pages (None = toutes) : miniatures à refaire
    layoutChanged = Signal()    # pages ajoutées, supprimées ou déplacées

    def __init__(self, doc, history: History, config, pdf_source=None, debug_perf: bool = False):
        super().__init__()
        self.doc, self.history, self.config = doc, history, config
        self.curve = PressureCurve(config.pressure_curve)
        self.renderer = PageRenderer(doc, self.curve, pdf_source)
        self.zoom = 1.0
        self.fit_width = True
        self.tool = None
        self.side_tool = None          # outil temporaire (bouton latéral / bout gomme)
        self._active = None            # outil du geste en cours
        self._cache: dict[str, tuple[float, QImage]] = {}
        self._tops: list[float] = []
        self._content_w = self._content_h = 0.0
        self._live: QImage | None = None
        self._hover: QPointF | None = None
        self._touch: dict | None = None
        self._current_page = 0
        self.overlays = []              # objets avec paint(painter) : règle, sélection…
        self.hidden_ids: set[str] = set()  # éléments masqués (sélection en cours de déplacement)
        self.debug_perf = debug_perf
        self._frames: list[float] = []
        self._last_paint_ms = 0.0

        vp = self.viewport()
        vp.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents)
        vp.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        vp.setMouseTracking(True)
        vp.setTabletTracking(True)
        router().proximityChanged.connect(self._on_proximity)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAcceptDrops(True)
        self.setFrameShape(QAbstractScrollArea.Shape.NoFrame)
        self.verticalScrollBar().setSingleStep(40)
        self.horizontalScrollBar().setSingleStep(40)

        self._sharp_timer = QTimer(self, singleShot=True, interval=SHARP_DELAY_MS, timeout=self._sharpen_next)
        self._long = QTimer(self, singleShot=True, interval=LONG_PRESS_MS, timeout=self._on_long_press)
        self._long_at = QPointF()
        self._held = False  # appui long servi : le contact en cours ne dessine plus rien
        self.ruler = Ruler(self)
        self.overlays.append(self.ruler)
        self._relayout()

    # ================= mise en page =================
    def _relayout(self):
        n_before = len(self._tops)
        y, self._tops = 0.0, []
        for p in self.doc.pages:
            self._tops.append(y)
            y += p.height + GAP
        self._content_h = max(0.0, y - GAP)
        self._content_w = max((p.width for p in self.doc.pages), default=595.0)
        if self.fit_width:
            self._apply_fit_width()
        self._update_scrollbars()
        self.viewport().update()
        if n_before and n_before != len(self._tops) or getattr(self, "_order", None) != [p.id for p in self.doc.pages]:
            self._order = [p.id for p in self.doc.pages]
            self.layoutChanged.emit()

    def _apply_fit_width(self):
        vw = max(self.viewport().width(), 200)
        self.zoom = max(MIN_ZOOM, min(MAX_ZOOM, vw / (self._content_w + 2 * MARGIN)))

    def _update_scrollbars(self):
        vw, vh = self.viewport().width(), self.viewport().height()
        total_w = (self._content_w + 2 * MARGIN) * self.zoom
        total_h = (self._content_h + 2 * MARGIN) * self.zoom
        self.horizontalScrollBar().setRange(0, max(0, int(total_w - vw)))
        self.horizontalScrollBar().setPageStep(vw)
        self.verticalScrollBar().setRange(0, max(0, int(total_h - vh)))
        self.verticalScrollBar().setPageStep(vh)

    def _x0(self) -> float:
        vw = self.viewport().width()
        total_w = (self._content_w + 2 * MARGIN) * self.zoom
        return max(0.0, (vw - total_w) / 2) + MARGIN * self.zoom - self.horizontalScrollBar().value()

    def page_rect(self, i: int) -> QRectF:
        p = self.doc.pages[i]
        x = self._x0() + (self._content_w - p.width) / 2 * self.zoom
        y = (MARGIN + self._tops[i]) * self.zoom - self.verticalScrollBar().value()
        return QRectF(x, y, p.width * self.zoom, p.height * self.zoom)

    def visible_pages(self) -> list[int]:
        h = self.viewport().height()
        return [i for i in range(len(self.doc.pages))
                if (r := self.page_rect(i)).bottom() >= 0 and r.top() <= h]

    def view_to_page(self, pos: QPointF, index: int | None = None) -> tuple[int, QPointF]:
        """Position écran → (page, point de page). index force la page (trait commencé)."""
        if index is None:
            y_doc = (pos.y() + self.verticalScrollBar().value()) / self.zoom - MARGIN
            index = 0
            for i, top in enumerate(self._tops):
                if y_doc >= top - GAP / 2:
                    index = i
        r = self.page_rect(index)
        return index, QPointF((pos.x() - r.x()) / self.zoom, (pos.y() - r.y()) / self.zoom)

    def page_to_view(self, index: int, x: float, y: float) -> QPointF:
        r = self.page_rect(index)
        return QPointF(r.x() + x * self.zoom, r.y() + y * self.zoom)

    def current_page(self) -> int:
        vis = self.visible_pages()
        if not vis:
            return 0
        mid = self.viewport().height() / 2
        return min(vis, key=lambda i: abs(self.page_rect(i).center().y() - mid))

    def scroll_to_page(self, i: int):
        self.verticalScrollBar().setValue(int((MARGIN + self._tops[i]) * self.zoom - 8))

    # ================= zoom =================
    def set_zoom(self, zoom: float, anchor: QPointF | None = None):
        zoom = max(MIN_ZOOM, min(MAX_ZOOM, zoom))
        if abs(zoom - self.zoom) < 1e-4:
            return
        anchor = anchor or QPointF(self.viewport().width() / 2, self.viewport().height() / 2)
        # Point du document sous l'ancre, gardé fixe.
        dx = (anchor.x() - self._x0()) / self.zoom
        dy = (anchor.y() + self.verticalScrollBar().value()) / self.zoom
        self.fit_width = False
        self.zoom = zoom
        self._update_scrollbars()
        vw = self.viewport().width()
        total_w = (self._content_w + 2 * MARGIN) * zoom
        center_pad = max(0.0, (vw - total_w) / 2) + MARGIN * zoom
        self.horizontalScrollBar().setValue(int(center_pad + dx * zoom - anchor.x()))
        self.verticalScrollBar().setValue(int(dy * zoom - anchor.y()))
        self._sharp_timer.start()
        self.zoomChanged.emit(self.zoom)
        self.viewport().update()

    def zoom_fit_width(self):
        self.fit_width = True
        self._relayout()
        self._sharp_timer.start()
        self.zoomChanged.emit(self.zoom)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._relayout()
        self._sharp_timer.start()

    def scrollContentsBy(self, dx, dy):
        self.viewport().update()
        cur = self.current_page()
        if cur != self._current_page:
            self._current_page = cur
            self.pageChanged.emit(cur)

    # ================= caches =================
    def _dpr(self) -> float:
        return self.viewport().devicePixelRatioF()

    def invalidate(self, page_ids=None):
        if page_ids is None:
            self._cache.clear()
        else:
            for pid in page_ids:
                self._cache.pop(pid, None)
        self.pagesInvalidated.emit(None if page_ids is None else set(page_ids))
        self.viewport().update()

    def _page_image(self, i: int) -> QImage:
        page = self.doc.pages[i]
        entry = self._cache.get(page.id)
        if entry is None:
            img = self.renderer.render_page(page, self.zoom, self._dpr(), self.hidden_ids)
            self._cache[page.id] = (self.zoom, img)
            return img
        if abs(entry[0] - self.zoom) > 1e-4:
            self._sharp_timer.start()  # image floue mise à l'échelle en attendant
        return entry[1]

    def _sharpen_next(self):
        """Recalcule une page nette à la fois (garde l'interface réactive)."""
        vis = self.visible_pages()
        for i in vis:
            page = self.doc.pages[i]
            entry = self._cache.get(page.id)
            if entry is None or abs(entry[0] - self.zoom) > 1e-4:
                self._cache[page.id] = (self.zoom, self.renderer.render_page(page, self.zoom, self._dpr(), self.hidden_ids))
                self.viewport().update(self.page_rect(i).toAlignedRect())
                self._sharp_timer.start(0)
                return
        # Libère les pages lointaines.
        if vis:
            keep = {self.doc.pages[j].id for j in range(max(0, vis[0] - CACHE_KEEP),
                                                       min(len(self.doc.pages), vis[-1] + CACHE_KEEP + 1))}
            for pid in list(self._cache):
                if pid not in keep:
                    del self._cache[pid]

    def bake(self, index: int, elements) -> None:
        """Ajoute des éléments au cache de la page sans tout repeindre, si l'ordre des calques le permet."""
        page = self.doc.pages[index]
        entry = self._cache.get(page.id)
        on_top = all(Page.layer_for(e) == "shapes" or (Page.layer_for(e) == "ink" and not page.shapes)
                     for e in elements)
        if entry is None or not on_top:
            self.invalidate({page.id})
            return
        scale, img = entry
        p = QPainter(img)
        p.scale(scale, scale)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        for e in elements:
            self.renderer.paint_element(p, e)
        p.end()
        self.pagesInvalidated.emit({page.id})

    def set_curve(self, points):
        self.curve = PressureCurve(points)
        self.renderer.set_curve(self.curve)
        self.invalidate()

    # ================= overlay du trait en cours =================
    def begin_live(self):
        dpr = self._dpr()
        vp = self.viewport()
        img = QImage(max(1, int(vp.width() * dpr)), max(1, int(vp.height() * dpr)),
                     QImage.Format.Format_ARGB32_Premultiplied)
        img.setDevicePixelRatio(dpr)
        img.fill(Qt.GlobalColor.transparent)
        self._live = img

    def live_painter(self, clear: bool = False) -> QPainter:
        if self._live is None:
            self.begin_live()
        if clear:
            self._live.fill(Qt.GlobalColor.transparent)
        p = QPainter(self._live)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        return p

    def end_live(self):
        self._live = None
        self.viewport().update()

    # ================= modifications =================
    def apply(self, cmd: Command, emit: bool = True) -> set[str]:
        n = len(self.doc.pages)
        touched = self.history.push(cmd)
        self._after_change(touched, n, emit)
        return touched

    def _after_change(self, touched, n_pages_before, emit=True):
        if len(self.doc.pages) != n_pages_before or self._order != [p.id for p in self.doc.pages]:
            self._relayout()
        self.invalidate(touched)
        if emit:
            self.changed.emit()

    def commit_elements(self, index: int, elements) -> None:
        """Valide des éléments dessinés : undo, cache, page ajoutée en bas si besoin."""
        page = self.doc.pages[index]
        self.history.begin_group()
        self.history.push(AddElements(page.id, elements))
        grew = index == len(self.doc.pages) - 1
        if grew:  # on écrit sur la dernière page : une page vierge apparaît dessous
            bg = next_background(page, self.config.default_background)
            self.history.push(AddPage(index + 1, Page(width=page.width, height=page.height, background=bg)))
        self.history.end_group()
        self.bake(index, elements)
        self.end_live()
        if grew:
            self._relayout()
        self.changed.emit()

    def _drop_selection(self):
        for t in (self.tool, self.side_tool):
            if t is not None and hasattr(t, "clear"):
                t.clear()

    def undo(self):
        self._cancel_gesture()
        self._drop_selection()
        n = len(self.doc.pages)
        self._after_change(self.history.undo(), n)

    def redo(self):
        self._cancel_gesture()
        self._drop_selection()
        n = len(self.doc.pages)
        self._after_change(self.history.redo(), n)

    # ================= outils =================
    def set_tool(self, tool):
        self._cancel_gesture()
        if self.tool is not None and self.tool is not tool:
            self.tool.dispose()
        self.tool = tool
        self.viewport().update()

    def _cancel_gesture(self):
        if self._active is not None:
            self._active.cancel()
            self._active = None
        self.end_live()

    def _start(self, tool, pos, pressure, t):
        if self.ruler.wants(pos):  # appui sur le corps ou la poignée de la règle
            tool = self.ruler
        if tool is None:
            return
        self._active = tool
        self._press = (QPointF(pos), time.monotonic())
        if getattr(tool, "long_press_menu", False) and getattr(tool, "_hit", lambda _: None)(pos) is None:
            self._long_start(pos)
        tool.press(pos, pressure, t)

    def _move(self, pos, pressure, t):
        self._long_track(pos)
        self._active.move(pos, pressure, t)

    def _finish(self, pos, pressure, t):
        self._long.stop()
        tool, self._active = self._active, None
        if tool is None:
            return
        if getattr(tool, "tap_selects_images", False) and self._tap_on_image(pos):
            tool.cancel()  # pas de point d'encre : l'appui servait à prendre l'image
            return
        tool.release(pos, pressure, t)
        self.toolFinished.emit()

    # ----- appui long -----
    def _long_start(self, pos: QPointF):
        self._long_at = QPointF(pos)
        self._long.start()

    def _long_track(self, pos: QPointF):
        if self._long.isActive() and math.hypot(pos.x() - self._long_at.x(), pos.y() - self._long_at.y()) > TAP_MOVE_PX:
            self._long.stop()

    def _on_long_press(self):
        """Stylet ou doigt immobile ~1 s : on annule le geste (pas de point d'encre) et on ouvre le menu."""
        self._cancel_gesture()
        self._held = True
        if self._touch is not None:
            self._touch.update(drawing=False, held=True)
        self._show_hover(None)
        index, pt = self.view_to_page(self._long_at)
        from ..controller.tools.lasso import element_at
        item = element_at(self.doc.pages[index], pt.x(), pt.y(), 10.0 / self.zoom)
        self.longPressed.emit(index, item, QPointF(self._long_at))

    def _tap_on_image(self, pos: QPointF, start: QPointF | None = None, t0: float | None = None) -> bool:
        """Appui bref et immobile sur une image : émet imageTapped et renvoie True."""
        start, t0 = (start, t0) if start is not None else getattr(self, "_press", (None, 0.0))
        if start is None or time.monotonic() - t0 > TAP_S:
            return False
        if math.hypot(pos.x() - start.x(), pos.y() - start.y()) > TAP_MOVE_PX:
            return False
        from ..controller.tools.lasso import image_at
        index, pt = self.view_to_page(pos)
        item = image_at(self.doc.pages[index], pt.x(), pt.y())
        if item is None:
            return False
        self.imageTapped.emit(index, item)
        return True

    # ================= peinture =================
    def paintEvent(self, event):
        t0 = time.perf_counter()
        p = QPainter(self.viewport())
        p.fillRect(event.rect(), QColor(style.colors()["desk"]))
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        clip = QRectF(event.rect())
        for i in self.visible_pages():
            r = self.page_rect(i)
            if r.intersects(clip):
                p.drawImage(r, self._page_image(i))
        if self._live is not None:
            p.drawImage(QRectF(self.viewport().rect()), self._live)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        for ov in self.overlays:
            ov.paint(p)
        for tool in {self.tool, self._active, self.side_tool} - {None, self.ruler}:
            tool.paint_overlay(p)
        if self._hover is not None and self.config.hover_dot and self._active is None:
            tool = self.tool
            if tool is not None and tool.dot_color is not None:
                c = QColor(tool.dot_color)
                c.setAlpha(180)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(c)
                p.drawEllipse(self._hover, 2.5, 2.5)
        if self.debug_perf:
            self._paint_perf(p, t0)
        p.end()

    def _paint_perf(self, p: QPainter, t0: float):
        now = time.perf_counter()
        self._frames = [f for f in self._frames if now - f < 1.0] + [now]
        self._last_paint_ms = (now - t0) * 1000
        text = f"{len(self._frames)} fps · peinture {self._last_paint_ms:.1f} ms · zoom {self.zoom:.2f} · cache {len(self._cache)}"
        p.setPen(QColor("#ffffff"))
        p.fillRect(QRectF(6, 6, 330, 22), QColor(0, 0, 0, 160))
        p.drawText(QRectF(12, 6, 320, 22), Qt.AlignmentFlag.AlignVCenter, text)
        QTimer.singleShot(250, lambda: self.viewport().update(QRect(6, 6, 330, 22)))

    def _set_hover(self, pos: QPointF | None):
        old, self._hover = self._hover, pos
        for q in filter(None, (old, pos)):
            self.viewport().update(int(q.x()) - 5, int(q.y()) - 5, 11, 11)

    # ================= entrées =================
    def _over_child(self, pos: QPointF) -> bool:
        """Vrai si pos tombe sur un widget posé sur la page (barre de sélection…)."""
        return self.viewport().childAt(pos.toPoint()) is not None

    def viewportEvent(self, e):
        t = e.type()
        if t in (QEvent.Type.TabletPress, QEvent.Type.TabletMove, QEvent.Type.TabletRelease):
            if self._active is None and t != QEvent.Type.TabletMove and self._over_child(e.position()):
                e.ignore()  # le bouton recevra le clic synthétisé par Qt
                return False
            self._tablet(e)
            return True
        if t in (QEvent.Type.TouchBegin, QEvent.Type.TouchUpdate, QEvent.Type.TouchEnd, QEvent.Type.TouchCancel):
            if t == QEvent.Type.TouchBegin and self._active is None and self._over_child(e.points()[0].position()):
                e.ignore()
                return False
            self._touch_event(e)
            return True
        return super().viewportEvent(e)

    def _tablet(self, e):
        e.accept()  # pas d'événement souris synthétisé
        pos, pressure, t = e.position(), e.pressure(), float(e.timestamp())
        t_ = e.type()
        # Bouton latéral maintenu (ou bout gomme) : la gomme est « armée », comme le stylo en survol.
        side = self.side_tool is not None and (e.pointingDevice().pointerType() == _ERASER_POINTER
                                               or bool(e.buttons() & ~Qt.MouseButton.LeftButton))
        tip = e.button() == Qt.MouseButton.LeftButton
        if self._held and t_ != QEvent.Type.TabletPress:  # appui long servi : rien jusqu'au lever du stylet
            if t_ == QEvent.Type.TabletRelease or not e.buttons():
                self._held = False
            return
        self._held = False
        if t_ == QEvent.Type.TabletPress and tip and self._active is None:
            self._set_hover(None)
            self._start(self.side_tool if side else self.tool, pos, pressure, t)
        elif t_ == QEvent.Type.TabletMove and self._active is not None:
            self._move(pos, pressure, t)
        elif t_ == QEvent.Type.TabletMove and e.buttons() & Qt.MouseButton.LeftButton and pressure > 0:
            self._set_hover(None)  # contact sans TabletPress (certains pilotes) : on démarre ici
            self._start(self.side_tool if side else self.tool, pos, pressure, t)
        elif t_ == QEvent.Type.TabletRelease and tip and self._active is not None:
            self._finish(pos, pressure, t)
        if self._active is None:  # survol : seulement montrer l'outil, jamais modifier la note
            self._show_hover(pos, side)

    def _on_proximity(self, near: bool):
        if not near:
            self._show_hover(None)

    def _show_hover(self, pos: QPointF | None, side: bool = False):
        """Point discret du stylo, ou cercle de la gomme quand le bouton est maintenu."""
        if side:
            self._set_hover(None)
            if self.tool is not None and self.tool is not self.side_tool:
                self.tool.hover(None)
            self.side_tool.hover(pos)
        else:
            if self.side_tool is not None and self.side_tool is not self.tool:
                self.side_tool.hover(None)
            self._set_hover(pos)
            if self.tool is not None:
                self.tool.hover(pos)

    def leaveEvent(self, e):
        self._show_hover(None)
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if router().mouse_blocked():
            return
        if e.button() == Qt.MouseButton.LeftButton:
            self._start(self.tool, e.position(), 0.5, float(e.timestamp()))
        elif e.button() == Qt.MouseButton.MiddleButton:
            self._pan_from = e.position()
        elif e.button() == Qt.MouseButton.RightButton and self.side_tool is not None:
            self._start(self.side_tool, e.position(), 0.5, float(e.timestamp()))

    def mouseMoveEvent(self, e):
        if router().mouse_blocked():
            return
        if self._active is not None:
            self._move(e.position(), 0.5, float(e.timestamp()))
        elif e.buttons() & Qt.MouseButton.MiddleButton and getattr(self, "_pan_from", None) is not None:
            d = e.position() - self._pan_from
            self._pan_from = e.position()
            self._scroll_by(-d.x(), -d.y())

    def mouseReleaseEvent(self, e):
        self._held = False
        if self._active is not None:
            self._finish(e.position(), 0.5, float(e.timestamp()))
        self._pan_from = None

    def wheelEvent(self, e):
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            steps = e.angleDelta().y() / 120
            self.set_zoom(self.zoom * (1.15 ** steps), e.position())
        else:
            super().wheelEvent(e)

    def _scroll_by(self, dx: float, dy: float):
        h, v = self.horizontalScrollBar(), self.verticalScrollBar()
        h.setValue(int(h.value() + dx))
        v.setValue(int(v.value() + dy))

    def _touch_event(self, e):
        e.accept()
        if router().palm_blocked():  # rejet de la paume
            self._touch = None
            return
        pts = [p for p in e.points() if p.state() != p.State.Released] if e.type() != QEvent.Type.TouchEnd else []
        if e.type() in (QEvent.Type.TouchEnd, QEvent.Type.TouchCancel) or not pts:
            self._long.stop()
            self._held = False
            tc = self._touch
            if tc and tc.get("drawing") and self._active is not None:
                self._finish(tc["last"], 0.5, float(e.timestamp()))
            elif tc and tc.get("n") == 1 and not tc.get("ruler") and not tc.get("held") and e.type() == QEvent.Type.TouchEnd:
                self._tap_on_image(tc["last"], tc["start"], tc["t0"])  # doigt : toucher une image la sélectionne
            self._touch = None
            return
        if len(pts) == 1:
            pos = pts[0].position()
            if self._touch is None or self._touch.get("n") != 1:
                on_ruler = self.ruler.visible and self.ruler.geom.contains(pos.x(), pos.y())
                # Un doigt sur une sélection du lasso la déplace / redimensionne (poignées larges).
                on_selection = (self._active is None and not on_ruler and self.tool is not None
                                and getattr(self.tool, "_hit", lambda _: None)(pos) is not None)
                drawing = (self.config.finger_draws or on_selection) and self._active is None and not on_ruler
                self._touch = {"n": 1, "last": pos, "drawing": drawing, "ruler": on_ruler,
                               "start": QPointF(pos), "t0": time.monotonic()}
                if drawing:
                    self._start(self.tool, pos, 0.5, float(e.timestamp()))
                elif not on_ruler:
                    self._long_start(pos)  # doigt qui fait défiler : l'appui long ouvre aussi le menu
                return
            if self._touch.get("held"):
                return
            self._long_track(pos)
            if self._touch["drawing"]:
                if self._active is not None:
                    self._move(pos, 0.5, float(e.timestamp()))
            elif self._touch.get("ruler"):
                d = pos - self._touch["last"]
                self.ruler.translate(d.x(), d.y())
                self.viewport().update()
            else:
                d = pos - self._touch["last"]
                self._scroll_by(-d.x(), -d.y())
            self._touch["last"] = pos
            return
        # Deux doigts : pincement pour zoomer + déplacement.
        a, b = pts[0].position(), pts[1].position()
        center = (a + b) / 2
        dist = max(1.0, math.hypot(a.x() - b.x(), a.y() - b.y()))
        angle = math.degrees(math.atan2(b.y() - a.y(), b.x() - a.x()))
        if self._touch is None or self._touch.get("n") != 2:
            self._long.stop()
            if self._touch and self._touch.get("drawing"):
                self._cancel_gesture()
            on_ruler = self.ruler.visible and self.ruler.geom.contains(center.x(), center.y())
            if on_ruler:
                self.ruler.begin_rotate()
            self._touch = {"n": 2, "center": center, "dist": dist, "last": center, "angle": angle, "ruler": on_ruler}
            return
        if self._touch.get("ruler"):  # deux doigts sur la règle : la déplacer et la pivoter
            d = center - self._touch["center"]
            self.ruler.translate(d.x(), d.y())
            da = (angle - self._touch["angle"] + 180) % 360 - 180
            self.ruler.rotate_by(da)
            self._touch.update(center=center, angle=angle)
            return
        self.set_zoom(self.zoom * dist / self._touch["dist"], center)
        d = center - self._touch["center"]
        self._scroll_by(-d.x(), -d.y())
        self._touch.update(center=center, dist=dist, last=center)

    # ----- glisser-déposer d'images -----
    @staticmethod
    def _dropped_image(mime):
        from ..controller import images
        if mime.hasImage():
            return QImage(mime.imageData())
        for url in mime.urls():
            if url.isLocalFile() and url.toLocalFile().lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")):
                return images.load_file(url.toLocalFile())
        return None

    def dragEnterEvent(self, e):
        m = e.mimeData()
        if m.hasImage() or any(u.isLocalFile() for u in m.urls()):
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        e.acceptProposedAction()

    def dropEvent(self, e):
        from ..controller import images
        img = self._dropped_image(e.mimeData())
        if img is not None and not img.isNull():
            images.add_image(self, img, e.position())
            e.acceptProposedAction()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape and self._active is not None:
            self._cancel_gesture()
        else:
            super().keyPressEvent(e)

