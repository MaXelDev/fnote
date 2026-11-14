"""Panneau des pages : miniatures, réorganisation par glisser-déposer, insertion, suppression, fonds."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QHBoxLayout, QListWidget, QListWidgetItem,
                               QPushButton, QVBoxLayout, QWidget)

from ..model.document import Page
from ..model.history import AddPage, MovePage, RemovePage, SetBackground

THUMB_W = 120
BACKGROUNDS = [("blank", "Blanc"), ("lined", "Ligné"), ("grid", "Quadrillé 5 mm"), ("dots", "Pointillé")]


class PagesPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.canvas = None
        self._thumbs: dict[str, QIcon] = {}
        self._dirty: set[str] = set()
        self.setMinimumWidth(THUMB_W + 48)

        self.list = QListWidget()
        self.list.setViewMode(QListWidget.ViewMode.IconMode)
        self.list.setFlow(QListWidget.Flow.TopToBottom)
        self.list.setWrapping(False)
        self.list.setIconSize(QSize(THUMB_W, int(THUMB_W * 1.42)))
        self.list.setSpacing(6)
        self.list.setMovement(QListWidget.Movement.Snap)
        self.list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.list.model().rowsMoved.connect(self._rows_moved)
        self.list.itemClicked.connect(lambda it: self.canvas and self.canvas.scroll_to_page(self.list.row(it)))

        add = QPushButton("+ Page")
        add.setToolTip("Insérer une page vierge après la page sélectionnée")
        add.clicked.connect(self.insert_page)
        delete = QPushButton("Supprimer")
        delete.clicked.connect(self.delete_page)
        self.bg = QComboBox()
        for key, label in BACKGROUNDS:
            self.bg.addItem(label, key)
        self.bg.setToolTip("Fond de la page sélectionnée")
        self.bg.activated.connect(lambda _: self.set_background(all_pages=False))
        all_btn = QPushButton("À toutes")
        all_btn.setToolTip("Appliquer ce fond à toutes les pages (hors pages PDF)")
        all_btn.clicked.connect(lambda: self.set_background(all_pages=True))

        row1, row2 = QHBoxLayout(), QHBoxLayout()
        row1.addWidget(add)
        row1.addWidget(delete)
        row2.addWidget(self.bg, 1)
        row2.addWidget(all_btn)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.addWidget(self.list, 1)
        lay.addLayout(row1)
        lay.addLayout(row2)
        self._timer = QTimer(self, singleShot=True, interval=400, timeout=self._refresh_dirty)

    # ----- liaison avec le canevas -----
    def set_canvas(self, canvas):
        if self.canvas is not None:
            for sig, slot in ((self.canvas.pagesInvalidated, self._invalidated),
                              (self.canvas.layoutChanged, self.rebuild), (self.canvas.pageChanged, self._select)):
                try:
                    sig.disconnect(slot)
                except (RuntimeError, TypeError):
                    pass
        self.canvas = canvas
        self._thumbs.clear()
        if canvas is not None:
            canvas.pagesInvalidated.connect(self._invalidated)
            canvas.layoutChanged.connect(self.rebuild)
            canvas.pageChanged.connect(self._select)
        self.rebuild()

    def _thumb(self, page: Page) -> QIcon:
        icon = self._thumbs.get(page.id)
        if icon is None:
            scale = THUMB_W / page.width
            img = self.canvas.renderer.render_page(page, scale, self.devicePixelRatioF())
            pm = QPixmap.fromImage(img)
            icon = QIcon(pm)
            icon.addPixmap(pm, QIcon.Mode.Selected)  # pas de teinte bleue sur la page sélectionnée
            self._thumbs[page.id] = icon
        return icon

    def rebuild(self):
        self.list.blockSignals(True)
        self.list.clear()
        if self.canvas is not None and self.isVisible():
            for i, page in enumerate(self.canvas.doc.pages):
                item = QListWidgetItem(self._thumb(page), str(i + 1))
                item.setData(Qt.ItemDataRole.UserRole, page.id)
                item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
                self.list.addItem(item)
            self._select(self.canvas.current_page())
        self.list.blockSignals(False)

    def showEvent(self, e):
        super().showEvent(e)
        self.rebuild()

    def _invalidated(self, ids):
        if ids is None:
            self._thumbs.clear()
            self._dirty = {p.id for p in self.canvas.doc.pages}
        else:
            for pid in ids:
                self._thumbs.pop(pid, None)
            self._dirty |= set(ids)
        if self.isVisible():
            self._timer.start()

    def _refresh_dirty(self):
        if self.canvas is None:
            return
        ids, self._dirty = self._dirty, set()
        for row in range(self.list.count()):
            item = self.list.item(row)
            pid = item.data(Qt.ItemDataRole.UserRole)
            if pid in ids:
                page = next((p for p in self.canvas.doc.pages if p.id == pid), None)
                if page is not None:
                    item.setIcon(self._thumb(page))

    def _select(self, index: int):
        if 0 <= index < self.list.count():
            self.list.setCurrentRow(index)
            page = self.canvas.doc.pages[index]
            k = self.bg.findData(page.background.get("kind"))
            self.bg.setCurrentIndex(max(k, 0))

    def _selected_index(self) -> int:
        row = self.list.currentRow()
        return row if row >= 0 else (self.canvas.current_page() if self.canvas else 0)

    # ----- actions -----
    def _rows_moved(self, _parent, start, _end, _dest, row):
        dst = row if row < start else row - 1
        if self.canvas is not None and dst != start:
            self.canvas.apply(MovePage(start, dst))
            self.canvas.scroll_to_page(dst)

    def insert_page(self):
        if self.canvas is None:
            return
        i = self._selected_index()
        ref = self.canvas.doc.pages[i]
        bg = ref.background if ref.background.get("kind") != "pdf" else {"kind": self.canvas.config.default_background}
        self.canvas.apply(AddPage(i + 1, Page(width=ref.width, height=ref.height, background=dict(bg))))
        self.canvas.scroll_to_page(i + 1)

    def delete_page(self):
        if self.canvas is None or len(self.canvas.doc.pages) <= 1:
            return
        self.canvas.apply(RemovePage(self.canvas.doc.pages[self._selected_index()]))

    def set_background(self, all_pages: bool):
        if self.canvas is None:
            return
        kind = self.bg.currentData()
        pages = self.canvas.doc.pages
        targets = [p for p in pages if p.background.get("kind") != "pdf"] if all_pages \
            else [pages[self._selected_index()]]
        targets = [p for p in targets if p.background.get("kind") != "pdf"]
        if targets:
            self.canvas.apply(SetBackground(targets, {"kind": kind}))
