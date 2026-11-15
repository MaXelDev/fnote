"""Images insérées : normalisation en PNG, dédoublonnage par empreinte, placement sur la page."""
from __future__ import annotations

import hashlib

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, Qt
from PySide6.QtGui import QImage

from ..model.elements import ImageItem
from ..model.history import AddElements

MAX_SIDE = 4096          # au-delà, l'image est réduite (poids du fichier, mémoire)
MAX_INPUT = 64 * 2**20   # fichier source refusé au-delà
IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif)"


def to_png(img: QImage) -> bytes | None:
    if img.isNull():
        return None
    if max(img.width(), img.height()) > MAX_SIDE:
        img = img.scaled(MAX_SIDE, MAX_SIDE, Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    return bytes(data.data())


def load_file(path: str) -> QImage:
    with open(path, "rb") as fh:
        raw = fh.read(MAX_INPUT + 1)
    if len(raw) > MAX_INPUT:
        return QImage()
    return QImage.fromData(raw)


def add_image(canvas, img: QImage, at_view: QPointF | None = None) -> ImageItem | None:
    """Ajoute l'image au document et la place (centrée sur at_view ou sur la page courante)."""
    png = to_png(img)
    if png is None:
        return None
    name = f"assets/{hashlib.sha1(png).hexdigest()}.png"
    canvas.doc.assets.setdefault(name, png)
    if at_view is not None:
        index, center = canvas.view_to_page(at_view)
    else:
        index = canvas.current_page()
        page = canvas.doc.pages[index]
        vis = canvas.page_rect(index)
        vh = canvas.viewport().height()
        cy = (min(vh, vis.bottom()) + max(0.0, vis.top())) / 2
        _, center = canvas.view_to_page(QPointF(vis.center().x(), cy), index)
    page = canvas.doc.pages[index]
    w = min(page.width * 0.6, img.width() * 0.75)  # 1 px ≈ 0,75 pt (96 dpi)
    h = w * img.height() / max(1, img.width())
    item = ImageItem(asset=name, rect=(center.x() - w / 2, center.y() - h / 2, w, h))
    canvas.apply(AddElements(page.id, [item]))
    return item
