"""Rendu des pages du PDF source en images (fonds de page), avec petit cache."""
from __future__ import annotations

import threading
from collections import OrderedDict

import pymupdf
from PySide6.QtGui import QImage

from .importer import open_pdf

CACHE_SIZE = 12


class PdfSource:
    def __init__(self, data: bytes):
        self._doc = open_pdf(data)
        self._lock = threading.Lock()  # un document PyMuPDF ne se partage pas entre threads
        self._cache: OrderedDict[tuple[int, int], QImage] = OrderedDict()

    @property
    def page_count(self) -> int:
        return self._doc.page_count

    def render(self, index: int, scale: float) -> QImage | None:
        """Page `index` à `scale` pixels par point (scale inclut le devicePixelRatio)."""
        if not 0 <= index < self._doc.page_count:
            return None
        key = (index, round(scale * 100))
        with self._lock:
            img = self._cache.get(key)
            if img is not None:
                self._cache.move_to_end(key)
                return img
            pix = self._doc[index].get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy()
            self._cache[key] = img
            while len(self._cache) > CACHE_SIZE:
                self._cache.popitem(last=False)
            return img
