import json
import zipfile

import pytest

from fnote.model import serialization as ser
from fnote.model.document import Document, Page
from fnote.model.elements import ImageItem, Shape, Stroke


def sample_doc():
    doc = Document(title="Analyse TD3")
    p = doc.pages[0]
    p.add(Stroke(points=[(10.123, 20.456, 0.4567, 0.0), (30, 40, 0.8, 16)], color="#1a1a1aff", width=1.6))
    p.add(Stroke(points=[(5, 5, 0.5, 0)], color="#ffe06673", width=14, tool="highlighter"))
    p.add(Shape(kind="rect", geometry=[(0, 0), (10, 0), (10, 10), (0, 10)], color="#d32f2fff"))
    doc.assets["assets/0123456789abcdef.png"] = b"\x89PNG fake"
    p.add(ImageItem(asset="assets/0123456789abcdef.png", rect=(1, 2, 3, 4)))
    doc.pages.append(Page(background={"kind": "grid"}))
    return doc


def test_round_trip(tmp_path):
    doc = sample_doc()
    path = tmp_path / "note.fnote"
    ser.save(doc, path)
    back = ser.load(path)
    assert back.title == "Analyse TD3"
    assert len(back.pages) == 2 and back.pages[1].background == {"kind": "grid"}
    p = back.pages[0]
    assert p.ink[0].points[0] == (10.12, 20.46, 0.457, 0.0)  # arrondi à l'écriture
    assert p.highlights[0].tool == "highlighter"
    assert p.shapes[0].kind == "rect" and p.images[0].rect == (1, 2, 3, 4)
    assert back.assets == doc.assets
    assert [e.id for e in p.elements()] == [e.id for e in doc.pages[0].elements()]


def test_round_trip_with_pdf(tmp_path):
    doc = Document(pages=[Page(background={"kind": "pdf", "pdf_page": 0})], source_pdf=b"%PDF-1.7 fake")
    ser.save(doc, tmp_path / "n.fnote")
    assert ser.load(tmp_path / "n.fnote").source_pdf == b"%PDF-1.7 fake"


def test_atomic_save_keeps_old_file_on_crash(tmp_path, monkeypatch):
    path = tmp_path / "note.fnote"
    ser.save(sample_doc(), path)
    before = path.read_bytes()

    def boom(*a, **k):
        raise RuntimeError("crash simulé")
    monkeypatch.setattr(ser, "_element_to_dict", boom)
    with pytest.raises(RuntimeError):
        ser.save(sample_doc(), path)
    assert path.read_bytes() == before
    assert [f.name for f in tmp_path.iterdir()] == ["note.fnote"]  # pas de temporaire oublié


def write_zip(path, doc_json, extra=None):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("document.json", json.dumps(doc_json))
        for name, data in (extra or {}).items():
            z.writestr(name, data)


def minimal(**over):
    d = {"format_version": 1, "pages": [{"id": "p1", "width": 595.28, "height": 841.89}]}
    d.update(over)
    return d


def test_future_version_refused(tmp_path):
    write_zip(tmp_path / "f.fnote", minimal(format_version=99))
    with pytest.raises(ser.FNoteFormatError, match="plus récente"):
        ser.load(tmp_path / "f.fnote")


def test_path_traversal_entries_are_ignored(tmp_path):
    write_zip(tmp_path / "z.fnote", minimal(), {"../../evil.sh": "rm -rf ~", "assets/../../x.png": "x"})
    doc = ser.load(tmp_path / "z.fnote")
    assert doc.assets == {}
    assert not (tmp_path.parent / "evil.sh").exists()


@pytest.mark.parametrize("bad", [
    {"format_version": "1"},
    minimal(pages=[]),
    minimal(pages=[{"id": "p", "width": 1, "height": 1, "background": {"kind": "wallpaper"}}]),
    minimal(pages=[{"id": "p", "width": 1, "height": 1, "background": {"kind": "pdf", "pdf_page": 0}}]),
    minimal(pages=[{"id": "p", "width": 1, "height": 1, "ink": [{"type": "stroke", "id": "s", "tool": "laser",
                                                              "color": "#000000ff", "width": 1, "points": [[0, 0, 0, 0]]}]}]),
    minimal(pages=[{"id": "p", "width": 1, "height": 1, "ink": [{"type": "stroke", "id": "s", "tool": "pencil",
                                                              "color": "red", "width": 1, "points": [[0, 0, 0, 0]]}]}]),
    minimal(pages=[{"id": "p", "width": float("nan"), "height": 1}]),
])
def test_invalid_documents_rejected(tmp_path, bad):
    write_zip(tmp_path / "b.fnote", bad)
    with pytest.raises(ser.FNoteFormatError):
        ser.load(tmp_path / "b.fnote")


def test_corrupt_file(tmp_path):
    (tmp_path / "c.fnote").write_bytes(b"pas un zip")
    with pytest.raises(ser.FNoteFormatError, match="corrompu"):
        ser.load(tmp_path / "c.fnote")


def test_oversized_entry_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(ser, "MAX_ASSET", 10)
    write_zip(tmp_path / "o.fnote", minimal(), {"assets/0123456789abcdef.png": b"x" * 100})
    with pytest.raises(ser.FNoteFormatError, match="volumineuse"):
        ser.load(tmp_path / "o.fnote")


def test_total_decompressed_budget(tmp_path, monkeypatch):
    monkeypatch.setattr(ser, "MAX_TOTAL", 150)
    extra = {f"assets/{i:016x}.png": b"x" * 60 for i in range(3)}
    write_zip(tmp_path / "t.fnote", minimal(), extra)
    with pytest.raises(ser.FNoteFormatError, match="volumineuse"):
        ser.load(tmp_path / "t.fnote")


def test_duplicate_ids_rejected(tmp_path):
    s = {"type": "stroke", "id": "same", "tool": "pencil", "color": "#000000ff", "width": 1, "points": [[0, 0, 0, 0]]}
    write_zip(tmp_path / "d.fnote", minimal(pages=[{"id": "p", "width": 1, "height": 1, "ink": [s, dict(s)]}]))
    with pytest.raises(ser.FNoteFormatError, match="double"):
        ser.load(tmp_path / "d.fnote")
