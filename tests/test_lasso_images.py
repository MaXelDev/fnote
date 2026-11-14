"""Lasso (sélection, déplacer, redimensionner, pivoter, actions) et images, sur le canevas hors écran."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PySide6.QtWidgets")
from PySide6.QtCore import QPointF  # noqa: E402
from PySide6.QtGui import QColor, QImage  # noqa: E402

from plume.controller import images  # noqa: E402
from plume.controller.tools.lasso import CLIPBOARD, LassoTool, paste  # noqa: E402
from plume.model.config import Config  # noqa: E402
from plume.model.document import Document, Page  # noqa: E402
from plume.model.elements import ImageItem, Stroke  # noqa: E402
from plume.model.history import History  # noqa: E402
from plume.view.canvas import Canvas  # noqa: E402
from plume.view.crop_dialog import combine_crop  # noqa: E402

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def setup():
    doc = Document(pages=[Page(), Page()])
    s = Stroke(points=[(100, 100, .5, 0), (200, 100, .5, 1)], width=2)
    doc.pages[0].add(s)
    c = Canvas(doc, History(doc), Config())
    c.resize(800, 900)
    c.show()
    app.processEvents()
    tool = LassoTool(c)
    c.set_tool(tool)
    return c, tool, s


def view(c, x, y):
    return c.page_to_view(0, x, y)


def drag(tool, a, b, steps=5):
    tool.press(a, .5, 0)
    for k in range(1, steps + 1):
        tool.move(a + (b - a) * (k / steps), .5, k)
    tool.release(b, .5, steps + 1)


def lasso_all(c, tool):
    pts = [view(c, 80, 80), view(c, 230, 80), view(c, 230, 130), view(c, 80, 130), view(c, 80, 80)]
    tool.press(pts[0], .5, 0)
    for p in pts[1:]:
        tool.move(p, .5, 1)
    tool.release(pts[-1], .5, 2)


def test_select_and_move_then_undo(setup):
    c, tool, s = setup
    lasso_all(c, tool)
    assert [e.id for e in tool.selection] == [s.id] and s.id in c.hidden_ids
    drag(tool, view(c, 150, 100), view(c, 170, 130))
    moved = c.doc.pages[0].ink[0]
    assert moved.id == s.id and abs(moved.points[0][0] - 120) < 0.5 and abs(moved.points[0][1] - 130) < 0.5
    c.undo()
    assert c.doc.pages[0].ink[0].points[0][:2] == (100, 100) and c.hidden_ids == set()


def test_scale_with_ratio_and_rotate(setup):
    c, tool, s = setup
    lasso_all(c, tool)
    x0, y0, x1, y1 = tool.box
    drag(tool, view(c, x1, y1), view(c, x0 + (x1 - x0) * 2, y1))  # coin bas-droit, double la largeur
    e = c.doc.pages[0].ink[0]
    length = e.points[-1][0] - e.points[0][0]
    assert 190 < length < 215 and e.width > 3  # proportions gardées : l'épaisseur suit
    tool.select([e], 0)
    cx = (tool.box[0] + tool.box[2]) / 2
    rh = tool._rotate_handle()
    center = view(c, cx, (tool.box[1] + tool.box[3]) / 2)
    drag(tool, rh, QPointF(center.x() + (rh.y() - center.y()) * -1, center.y()))  # quart de tour
    r = c.doc.pages[0].ink[0]
    assert abs(r.points[0][0] - r.points[-1][0]) < 2  # devenu vertical (aimanté à 90°)


def test_duplicate_delete_copy_paste(setup):
    c, tool, s = setup
    lasso_all(c, tool)
    tool.action("duplicate")
    assert len(c.doc.pages[0].ink) == 2
    tool.action("copy")
    tool.action("delete")
    assert len(c.doc.pages[0].ink) == 1
    assert CLIPBOARD["elements"] and paste(c, tool)
    assert len(c.doc.pages[c.current_page()].ink) >= 1


def test_recolor_and_thicker(setup):
    c, tool, s = setup
    lasso_all(c, tool)
    tool.recolor("#d32f2f")
    assert c.doc.pages[0].ink[0].color == "#d32f2fff"
    tool.action("thicker")
    assert c.doc.pages[0].ink[0].width > 2


def test_add_image_dedup_and_select(setup):
    c, tool, s = setup
    img = QImage(400, 200, QImage.Format.Format_RGB32)
    img.fill(QColor("#ff0000"))
    a = images.add_image(c, img)
    b = images.add_image(c, img)
    assert a.asset == b.asset and len(c.doc.assets) == 1
    page = c.doc.pages[c.current_page()]
    assert sum(isinstance(e, ImageItem) for e in page.images) == 2
    assert images.to_png(QImage()) is None


def test_huge_image_downscaled():
    img = QImage(5000, 100, QImage.Format.Format_RGB32)
    img.fill(QColor("#000000"))
    back = QImage.fromData(images.to_png(img))
    assert back.width() == images.MAX_SIDE


def test_combine_crop():
    assert combine_crop((0, 0, 1, 1), (0.25, 0.5, 0.75, 1)) == (0.25, 0.5, 0.75, 1)
    assert combine_crop((0.5, 0, 1, 0.5), (0, 0, 0.5, 1)) == (0.5, 0, 0.75, 0.5)
