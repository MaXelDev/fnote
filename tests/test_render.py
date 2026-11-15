"""Rendu Qt hors écran : la page est peinte, l'encre est noire, le surligneur passe sous l'encre."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PySide6.QtWidgets")

from fnote.engine.pressure import PressureCurve  # noqa: E402
from fnote.model.document import Document, Page  # noqa: E402
from fnote.model.elements import Shape, Stroke  # noqa: E402
from fnote.view.render import PageRenderer, qcolor  # noqa: E402

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def px(img, x, y):
    return img.pixelColor(x, y)


def test_qcolor_alpha():
    c = qcolor("#ffe06673")
    assert c.alpha() == 0x73 and c.red() == 0xff


def test_ink_over_highlight_and_backgrounds():
    page = Page(width=100, height=100, background={"kind": "grid"})
    page.add(Stroke(points=[(10, 50, 1, 0), (90, 50, 1, 1)], color="#000000ff", width=4, tool="ballpoint"))
    page.add(Stroke(points=[(10, 50, .5, 0), (90, 50, .5, 1)], color="#ffff00ff", width=20, tool="highlighter"))
    doc = Document(pages=[page])
    img = PageRenderer(doc, PressureCurve()).render_page(page, scale=1.0)
    ink = px(img, 50, 50)
    assert ink.red() < 40 and ink.green() < 40  # l'encre reste noire au-dessus du surligneur
    hl = px(img, 50, 42)
    assert hl.red() > 200 and hl.green() > 200 and hl.blue() < 80  # surligné jaune
    assert px(img, 95, 5).red() > 200  # fond blanc


def test_shapes_render():
    page = Page(width=100, height=100)
    page.add(Shape(kind="ellipse", geometry=[(20, 20), (80, 20), (80, 80), (20, 80)], color="#ff0000ff", width=3))
    img = PageRenderer(Document(pages=[page]), PressureCurve()).render_page(page, 1.0)
    edge = px(img, 50, 20)
    assert edge.red() > 200 and edge.green() < 80
    assert px(img, 50, 50).green() > 200  # intérieur vide
