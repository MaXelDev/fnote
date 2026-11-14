"""Canevas hors écran : tracé, page ajoutée en bas, cache, gomme, undo, conversions."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PySide6.QtWidgets")
from PySide6.QtCore import QPointF  # noqa: E402

from plume.controller.tools.eraser import EraserTool  # noqa: E402
from plume.controller.tools.ink import InkTool, straighten  # noqa: E402
from plume.model.config import Config  # noqa: E402
from plume.model.document import Document, Page  # noqa: E402
from plume.model.history import History  # noqa: E402
from plume.view.canvas import Canvas  # noqa: E402

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
PEN = {"tool": "fountain", "color": "#1a1a1aff", "width": 2.0}


def make(pages=2):
    doc = Document(pages=[Page() for _ in range(pages)])
    c = Canvas(doc, History(doc), Config())
    c.resize(800, 900)
    c.show()
    app.processEvents()
    return c


def draw(c, tool, pts):
    tool.press(QPointF(*pts[0]), 0.6, 0)
    for i, p in enumerate(pts[1:], 1):
        tool.move(QPointF(*p), 0.6, i * 5)
    tool.release(QPointF(*pts[-1]), 0.6, len(pts) * 5)


@pytest.mark.parametrize("zoom", [0.5, 1.0, 2.37])
def test_view_page_round_trip(zoom):
    c = make()
    c.set_zoom(zoom)
    c.verticalScrollBar().setValue(137)
    i, pt = c.view_to_page(QPointF(300, 250))
    back = c.page_to_view(i, pt.x(), pt.y())
    assert abs(back.x() - 300) < 1e-6 and abs(back.y() - 250) < 1e-6


def test_draw_stroke_and_undo():
    c = make(pages=2)
    pen = InkTool(c, PEN)
    c.set_tool(pen)
    r = c.page_rect(0)
    draw(c, pen, [(r.x() + 50, r.y() + 50), (r.x() + 150, r.y() + 80), (r.x() + 250, r.y() + 60)])
    assert len(c.doc.pages[0].ink) == 1 and len(c.doc.pages) == 2
    c.undo()
    assert c.doc.pages[0].ink == []


def test_writing_on_last_page_adds_one():
    c = make(pages=1)
    pen = InkTool(c, PEN)
    r = c.page_rect(0)
    draw(c, pen, [(r.x() + 20, r.y() + 20), (r.x() + 60, r.y() + 30)])
    assert len(c.doc.pages) == 2
    c.undo()  # trait et page ajoutée annulés ensemble
    assert len(c.doc.pages) == 1


def test_cache_only_touched_page_invalidated():
    c = make(pages=2)
    c.viewport().repaint()
    ids = [p.id for p in c.doc.pages]
    for pid in ids:
        c._cache.setdefault(pid, (c.zoom, c.renderer.render_page(c.doc.pages[0], c.zoom)))
    hl = InkTool(c, {"tool": "highlighter", "color": "#ffe06673", "width": 14})
    r = c.page_rect(0)
    draw(c, hl, [(r.x() + 20, r.y() + 20), (r.x() + 120, r.y() + 25)])
    assert ids[0] not in c._cache and ids[1] in c._cache  # surligneur : page 0 recalculée seule


def test_eraser_whole_and_partial_one_undo_step():
    c = make(pages=2)
    pen = InkTool(c, PEN)
    r = c.page_rect(0)
    y = r.y() + 100
    draw(c, pen, [(r.x() + 50, y), (r.x() + 350, y)])
    eraser = EraserTool(c, {"mode": "partial", "size": 6.0, "highlight_only": False})
    x = r.x() + 200
    draw(c, eraser, [(x, y - 40), (x, y + 40)])  # traverse en un seul segment rapide
    assert len(c.doc.pages[0].ink) == 2  # coupé en deux
    c.undo()
    assert len(c.doc.pages[0].ink) == 1
    eraser.spec["mode"] = "stroke"
    draw(c, eraser, [(x, y - 40), (x, y + 40)])
    assert c.doc.pages[0].ink == []


def test_highlight_only_eraser_keeps_ink():
    c = make()
    r = c.page_rect(0)
    y = r.y() + 100
    draw(c, InkTool(c, PEN), [(r.x() + 50, y), (r.x() + 350, y)])
    draw(c, InkTool(c, {"tool": "highlighter", "color": "#ffe06673", "width": 14}), [(r.x() + 50, y), (r.x() + 350, y)])
    eraser = EraserTool(c, {"mode": "stroke", "size": 6.0, "highlight_only": True})
    draw(c, eraser, [(r.x() + 200, y - 30), (r.x() + 200, y + 30)])
    assert c.doc.pages[0].highlights == [] and len(c.doc.pages[0].ink) == 1


def test_straight_highlighter():
    out = straighten([(10, 10, .5, 0), (50, 14, .5, 1), (90, 12, .5, 2)])
    assert out[0][:2] == (10, 12) and out[1][:2] == (90, 12)


def test_zoom_keeps_anchor():
    c = make()
    anchor = QPointF(400, 300)
    i, before = c.view_to_page(anchor)
    c.set_zoom(c.zoom * 2, anchor)
    _, after = c.view_to_page(anchor, i)
    assert abs(after.x() - before.x()) < 1.5 and abs(after.y() - before.y()) < 1.5


def test_paint_does_not_crash():
    c = make()
    c.debug_perf = True
    c.viewport().repaint()
    img = c.viewport().grab()
    assert not img.isNull()


def test_hold_converts_stroke_to_shape():
    c = make()
    pen = InkTool(c, PEN)
    r = c.page_rect(0)
    corners = [(100, 100), (300, 100), (300, 220), (100, 220), (100, 100)]
    pts = []
    for (ax, ay), (bx, by) in zip(corners, corners[1:]):
        pts += [(ax + (bx - ax) * k / 20, ay + (by - ay) * k / 20) for k in range(20)]
    pts = [(r.x() + x, r.y() + y) for x, y in pts]
    pen.press(QPointF(*pts[0]), .5, 0)
    for i, p in enumerate(pts[1:]):
        pen.move(QPointF(*p), .5, i)
    pen._on_hold()  # le minuteur de maintien a expiré
    pen.release(QPointF(*pts[-1]), .5, 999)
    page = c.doc.pages[0]
    assert len(page.shapes) == 1 and page.shapes[0].kind == "rect" and page.ink == []
    assert page.shapes[0].color == PEN["color"]


def test_stroke_snaps_to_ruler_edge():
    c = make()
    c.ruler.toggle()
    g = c.ruler.geom
    g.angle = 0.0
    edge_y = g.cy - g.thickness / 2
    pen = InkTool(c, PEN)
    pts = [(g.cx - 150 + i * 10, edge_y - 6 + (i % 3)) for i in range(30)]
    draw(c, pen, pts)
    s = c.doc.pages[c.view_to_page(QPointF(g.cx, edge_y))[0]].ink[-1]
    ys = {round(p[1], 6) for p in s.points}
    assert len(ys) == 1  # parfaitement droit, collé au bord


def test_ruler_body_drag_moves_ruler():
    c = make()
    c.ruler.toggle()
    g = c.ruler.geom
    x0 = g.cx
    c._start(InkTool(c, PEN), QPointF(g.cx - 100, g.cy), .5, 0)  # appui au milieu du corps
    c._active.move(QPointF(g.cx - 60, g.cy), .5, 1)
    c._finish(QPointF(g.cx - 60, g.cy), .5, 2)
    assert abs(g.cx - (x0 + 40)) < 1e-6 and all(not p.ink for p in c.doc.pages)


def test_stroke_ends_exactly_at_pen_lift():
    c = make()
    pen = InkTool(c, {"tool": "ballpoint", "color": "#000000ff", "width": 1.0})
    r = c.page_rect(0)
    draw(c, pen, [(r.x() + 100, r.y() + 100), (r.x() + 400, r.y() + 100)])  # deux échantillons seulement
    s = c.doc.pages[0].ink[0]
    end = c.page_to_view(0, s.points[-1][0], s.points[-1][1])
    assert abs(end.x() - (r.x() + 400)) < 0.5
