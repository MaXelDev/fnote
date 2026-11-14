"""Import d'un PDF : chaque page devient une page de note avec le PDF en fond."""
from __future__ import annotations

from pathlib import Path

import pymupdf

from ..model.document import Document, Page
from ..model.serialization import MAX_PDF


class PdfImportError(ValueError):
    pass


def open_pdf(data: bytes) -> pymupdf.Document:
    """Ouvre un PDF en mémoire, de façon défensive (fichier non fiable)."""
    try:
        src = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:  # PyMuPDF lève des types variés sur un fichier corrompu
        raise PdfImportError("PDF illisible ou corrompu") from exc
    if not src.is_pdf:
        raise PdfImportError("ce fichier n'est pas un PDF")
    if src.needs_pass:
        raise PdfImportError("PDF protégé par mot de passe : retire la protection puis réessaie")
    if src.page_count == 0:
        raise PdfImportError("PDF sans page")
    return src


def import_pdf(path: str | Path) -> Document:
    path = Path(path)
    with open(path, "rb") as fh:
        data = fh.read(MAX_PDF + 1)
    if len(data) > MAX_PDF:
        raise PdfImportError("PDF trop volumineux (plus de 512 Mo)")
    src = open_pdf(data)
    pages = [Page(width=float(p.rect.width), height=float(p.rect.height), background={"kind": "pdf", "pdf_page": i})
             for i, p in enumerate(src)]
    return Document(pages=pages, title=path.stem, source_pdf=data)


def note_path_for(pdf_path: Path) -> Path:
    """« Cours.pdf » → « Cours (annoté).plume » : le PDF compagnon ne remplacera jamais l'original."""
    base = pdf_path.with_name(f"{pdf_path.stem} (annoté)")
    candidate, k = base.with_suffix(".plume"), 2
    while candidate.exists():
        candidate = pdf_path.with_name(f"{pdf_path.stem} (annoté {k}).plume")
        k += 1
    return candidate
