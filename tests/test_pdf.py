"""Import / export PDF : texte d'origine sélectionnable, encre vectorielle, pages vierges, sécurité."""
import os

import pymupdf
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PySide6.QtWidgets")
from PySide6.QtGui import QColor, QImage  # noqa: E402

from plume.engine.pressure import PressureCurve  # noqa: E402
from plume.model import serialization  # noqa: E402
from plume.model.document import Document, Page  # noqa: E402
from plume.model.elements import ImageItem, Shape, Stroke  # noqa: E402
from plume.pdf.exporter import export_document, export_to_file, is_plume_pdf  # noqa: E402
from plume.pdf.importer import PdfImportError, import_pdf, note_path_for  # noqa: E402
from plume.pdf.source import PdfSource  # noqa: E402

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def make_pdf(path, pages=3, text="Théorème de Gauss", landscape_last=False):
    d = pymupdf.open()
    for i in range(pages):
        w, h = (842, 595) if landscape_last and i == pages - 1 else (595, 842)
        pg = d.new_page(width=w, height=h)
        pg.insert_text((72, 100), f"{text} page {i + 1}", fontsize=14)
    d.save(path)
    return path


def test_import_pages_and_sizes(tmp_path):
    doc = import_pdf(make_pdf(tmp_path / "td.pdf", 3, landscape_last=True))
    assert len(doc.pages) == 3 and doc.source_pdf
    assert [p.background for p in doc.pages] == [{"kind": "pdf", "pdf_page": i} for i in range(3)]
    assert doc.pages[2].width > doc.pages[2].height  # paysage conservé


def test_import_errors(tmp_path):
    (tmp_path / "bad.pdf").write_bytes(b"%PDF-1.7 garbage")
    with pytest.raises(PdfImportError):
        import_pdf(tmp_path / "bad.pdf")
    d = pymupdf.open()
    d.new_page()
    d.save(tmp_path / "locked.pdf", encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="x", owner_pw="y")
    with pytest.raises(PdfImportError, match="mot de passe"):
        import_pdf(tmp_path / "locked.pdf")


def test_note_path_never_overwrites_source(tmp_path):
    pdf = make_pdf(tmp_path / "Cours.pdf", 1)
    p = note_path_for(pdf)
    assert p.name == "Cours (annoté).plume" and p.with_suffix(".pdf") != pdf
    p.write_bytes(b"x")
    assert note_path_for(pdf).name == "Cours (annoté 2).plume"


def test_render_background():
    d = pymupdf.open()
    d.new_page()
    src = PdfSource(d.tobytes())
    img = src.render(0, 0.5)
    assert img.width() == round(595 * 0.5) and src.render(0, 0.5) is img  # cache
    assert src.render(5, 1) is None


def test_export_keeps_text_and_vector_ink(tmp_path):
    doc = import_pdf(make_pdf(tmp_path / "td.pdf", 2))
    doc.pages.insert(1, Page())  # page vierge insérée entre deux pages du PDF
    doc.pages[0].add(Stroke(points=[(100, 200, .3, 0), (300, 220, .9, 1)], color="#1f5fd1ff", width=2))
    doc.pages[0].add(Stroke(points=[(72, 95, .5, 0), (250, 95, .5, 1)], color="#ffe0668c", width=14,
                            tool="highlighter"))
    doc.pages[0].add(Shape(kind="ellipse", geometry=[(50, 50), (150, 50), (150, 100), (50, 100)], color="#d32f2fff"))
    img = QImage(40, 20, QImage.Format.Format_RGB32)
    img.fill(QColor("#00ff00"))
    from plume.controller.images import to_png
    doc.assets["assets/0123456789abcdef.png"] = to_png(img)
    doc.pages[1].add(ImageItem(asset="assets/0123456789abcdef.png", rect=(10, 10, 80, 40), rotation=30))
    out = pymupdf.open(stream=export_document(doc, PressureCurve()), filetype="pdf")
    assert out.page_count == 3
    assert "Théorème de Gauss page 1" in out[0].get_text()  # texte d'origine sélectionnable
    assert "page 2" in out[2].get_text()
    drawings = out[0].get_drawings()
    assert any(d.get("fill") and abs(d["fill"][2] - 0x1f / 255 * 0 - 0xd1 / 255) < 0.02 for d in drawings)
    assert not out[0].get_images()  # l'encre n'est pas une image
    assert out[1].get_images()       # l'image insérée, elle, en est une
    assert out.metadata["producer"] == "Plume"


def test_export_note_without_pdf_and_atomic_file(tmp_path):
    doc = Document(pages=[Page(background={"kind": "grid"}), Page(background={"kind": "lined"})])
    doc.pages[0].add(Stroke(points=[(10, 10, .5, 0), (100, 100, .5, 1)]))
    path = tmp_path / "Note.pdf"
    export_to_file(doc, PressureCurve(), path)
    assert is_plume_pdf(path) and pymupdf.open(path).page_count == 2
    other = make_pdf(tmp_path / "autre.pdf", 1)
    assert not is_plume_pdf(other)


def test_round_trip_plume_with_pdf(tmp_path):
    doc = import_pdf(make_pdf(tmp_path / "td.pdf", 2))
    serialization.save(doc, tmp_path / "td.plume")
    back = serialization.load(tmp_path / "td.plume")
    assert back.source_pdf == doc.source_pdf and back.pages[1].background["pdf_page"] == 1


def test_highlighter_uses_multiply_in_pdf():
    doc = Document(pages=[Page()])
    doc.pages[0].add(Stroke(points=[(72, 95, .5, 0), (250, 95, .5, 1)], color="#ffe0668c", width=14, tool="highlighter"))
    out = pymupdf.open(stream=export_document(doc, PressureCurve()), filetype="pdf")
    assert "/BM/Multiply" in out.xref_get_key(out[0].xref, "Resources/ExtGState")[1].replace(" ", "")


def test_companion_export_and_protection(tmp_path):
    from PySide6.QtCore import QThreadPool
    from plume.controller.document_controller import DocumentController
    from plume.model.config import Config
    from plume.pdf.companion import CompanionExporter
    ctl = DocumentController(Document(), tmp_path / "Note.plume", Config())
    exp = CompanionExporter()
    assert exp.export(ctl, PressureCurve())
    QThreadPool.globalInstance().waitForDone(10000)
    assert is_plume_pdf(tmp_path / "Note.pdf")
    # un PDF étranger du même nom n'est jamais écrasé
    make_pdf(tmp_path / "Cours.pdf", 1)
    before = (tmp_path / "Cours.pdf").read_bytes()
    skipped = []
    exp.skipped.connect(skipped.append)
    assert not exp.export(DocumentController(Document(), tmp_path / "Cours.plume", Config()), PressureCurve())
    assert skipped and (tmp_path / "Cours.pdf").read_bytes() == before
