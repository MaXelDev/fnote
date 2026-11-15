"""Génère les captures d'écran du README (hors écran, données fictives) :

    QT_QPA_PLATFORM=offscreen .venv/bin/python tools/captures.py docs/screenshots
"""
from __future__ import annotations

import math
import shutil
import sys
import tempfile
from pathlib import Path

import pymupdf
from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

app = QApplication([])

from fnote.controller.document_controller import DocumentController  # noqa: E402
from fnote.controller.tools.ink import InkTool  # noqa: E402
from fnote.controller.tools.lasso import LassoTool  # noqa: E402
from fnote.model import serialization  # noqa: E402
from fnote.model.config import Config  # noqa: E402
from fnote.model.document import Document, Page  # noqa: E402
from fnote.view import style  # noqa: E402
from fnote.view.main_window import MainWindow  # noqa: E402

style.apply(app)
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/screenshots")
OUT.mkdir(parents=True, exist_ok=True)
tmp = Path(tempfile.mkdtemp())
vault = tmp / "Vault"
for d in ("Analyse", "Électromagnétisme", "Réseaux"):
    (vault / d).mkdir(parents=True)
cfg = Config(vault_path=str(vault), default_background="lined")
cfg.save = lambda *a, **k: None  # ne touche pas à la vraie configuration


def handwriting(c, page, x, y, words, color, width=1.6, seed=0):
    """Pseudo-écriture : boucles régulières, pression variable."""
    pen = InkTool(c, {"tool": "fountain", "color": color, "width": width})
    for k, n in enumerate(words):
        pts = []
        for i in range(n * 9):
            t = i / 9
            pts.append((x + t * 7.5 + 2.2 * math.sin(t * 6.3 + seed + k),
                        y - 5 * abs(math.sin(t * 3.1 + seed * 0.7 + k)) + 1.5 * math.cos(t * 9.4 + k)))
        v = [c.page_to_view(page, *p) for p in pts]
        pen.press(v[0], .3, 0)
        for i, q in enumerate(v[1:]):
            pen.move(q, .35 + .55 * abs(math.sin(i / 6 + k)), i)
        pen.release(v[-1], .5, 999)
        x += n * 7.5 + 14


def stroke(c, page, spec, pts):
    t = InkTool(c, spec)
    v = [c.page_to_view(page, *p) for p in pts]
    t.press(v[0], .5, 0)
    for i, q in enumerate(v[1:]):
        t.move(q, .6, i)
    t.release(v[-1], .6, 999)
    return t


def window():
    w = MainWindow(cfg)
    w.resize(1366, 840)
    w.show()
    app.processEvents()
    return w


def save(w, name):
    app.processEvents()
    for tab in w.note_tabs():
        tab.canvas.viewport().repaint()
    w.grab().save(str(OUT / name))


# 1. Note de cours manuscrite
w = window()
path = vault / "Analyse" / "Intégrales généralisées.fnote"
doc = Document(pages=[Page(background={"kind": "lined"}), Page(background={"kind": "lined"})])
serialization.save(doc, path)
tab = w._add_tab(DocumentController(doc, path, cfg))
c = tab.canvas
handwriting(c, 0, 70, 95, [7, 4, 9, 6], "#1b2a6bff", 2.2)
stroke(c, 0, {"tool": "highlighter", "color": "#ffe0668c", "width": 14}, [(64 + i * 6, 92) for i in range(46)])
y = 140
for line, col in ((([5, 3, 8, 4, 6]), "#1a1a1aff"), ([6, 9, 3, 5], "#1a1a1aff"), ([4, 7, 6, 8, 3], "#1f5fd1ff"),
                  ([8, 5, 4, 6], "#1a1a1aff"), ([5, 6, 7], "#d32f2fff")):
    handwriting(c, 0, 70, y, line, col, seed=y)
    y += 22.7
box = [(64, 254), (300, 254), (300, 274), (64, 274), (64, 254)]
dense = [(a[0] + (b[0] - a[0]) * k / 40, a[1] + (b[1] - a[1]) * k / 40) for a, b in zip(box, box[1:]) for k in range(40)]
stroke(c, 0, {"tool": "ballpoint", "color": "#d32f2fff", "width": 1.4}, dense + [box[-1]])
save(w, "note.png")

# 1 bis. Appui long dans le vide : menu Coller / Insérer (fenêtre à part, collée sur la capture)
at = c.page_to_view(0, 330, 200)
w._long_press(tab, 0, None, at)
menu = w._long_menu
app.processEvents()
shot = w.grab().toImage()
painter = QPainter(shot)
painter.drawPixmap(c.viewport().mapTo(w, at.toPoint()), menu.grab())
painter.end()
menu.hide()
shot.save(str(OUT / "menu.png"))

# 2. Annoter un sujet de TD en PDF
pdf = pymupdf.open()
pg = pdf.new_page()
pg.insert_text((72, 80), "TD 3 - Equations de Maxwell", fontsize=18)
lines = ["Exercice 1. Montrer que le champ E derive d'un potentiel scalaire V.",
         "Exercice 2. Calculer le flux du champ magnetique a travers la surface S.",
         "Exercice 3. En deduire l'equation de propagation dans le vide."]
for i, t in enumerate(lines):
    pg.insert_text((72, 130 + i * 34), t, fontsize=12)
pdf.save(tmp / "TD3.pdf")
w.import_pdf(tmp / "TD3.pdf", vault / "Électromagnétisme")
tab = w.current_tab()
c = tab.canvas
stroke(c, 0, {"tool": "highlighter", "color": "#9be58a8c", "width": 13}, [(70 + i * 7, 126) for i in range(58)])
stroke(c, 0, {"tool": "highlighter", "color": "#ffe0668c", "width": 13}, [(70 + i * 7, 160) for i in range(62)])
handwriting(c, 0, 90, 250, [3, 5, 2, 6], "#1f5fd1ff", seed=3)
handwriting(c, 0, 90, 274, [6, 4, 7], "#1f5fd1ff", seed=8)
stroke(c, 0, {"tool": "ballpoint", "color": "#d32f2fff", "width": 1.4},
       [(395 + 52 * math.cos(a / 60 * 6.283), 199 + 13 * math.sin(a / 60 * 6.283)) for a in range(61)])
w.pages_dock.show()
save(w, "pdf.png")
w.pages_dock.hide()

# 3. Règle et formes
path = vault / "Réseaux" / "Topologies.fnote"
doc = Document(pages=[Page(background={"kind": "grid"})])
serialization.save(doc, path)
tab = w._add_tab(DocumentController(doc, path, cfg))
c = tab.canvas
pen = InkTool(c, {"tool": "fountain", "color": "#00838fff", "width": 1.8})
for cx, cy in ((150, 140), (330, 140), (240, 260)):
    pts = [c.page_to_view(0, cx + 32 * math.cos(a / 30 * 6.283), cy + 32 * math.sin(a / 30 * 6.283)) for a in range(31)]
    pen.press(pts[0], .5, 0)
    for i, q in enumerate(pts[1:]):
        pen.move(q, .5, i)
    pen._on_hold()
    pen.release(pts[-1], .5, 99)
for verts in ([(50, 320), (150, 320), (150, 380), (50, 380)],                        # rectangle
              [(455 + 40 * math.cos(k / 6 * 6.283), 110 + 40 * math.sin(k / 6 * 6.283)) for k in range(6)]):  # hexagone
    loop = verts + verts[:1]
    pts = [c.page_to_view(0, a[0] + (b[0] - a[0]) * t / 12, a[1] + (b[1] - a[1]) * t / 12)
           for a, b in zip(loop, loop[1:]) for t in range(12)] + [c.page_to_view(0, *loop[0])]
    pen.press(pts[0], .5, 0)
    for i, q in enumerate(pts[1:]):
        pen.move(q, .5, i)
    pen._on_hold()
    pen.release(pts[-1], .5, 99)
for a, b in (((182, 140), (298, 140)), ((170, 165), (220, 232)), ((310, 165), (260, 232))):
    stroke(c, 0, {"tool": "ballpoint", "color": "#1a1a1aff", "width": 1.3}, [a, b])
c.ruler.toggle()
g = c.ruler.geom
g.angle, g.cx, g.cy = 15.0, 760, 520
w.toolbar.set_checked("ruler", True)
save(w, "regle.png")

# 4. Lasso sur une image et du texte
lasso = LassoTool(c)
c.set_tool(lasso)
r = c.page_rect(0)
poly = [QPointF(r.x() + 60, r.y() + 60), QPointF(r.x() + 520, r.y() + 60), QPointF(r.x() + 520, r.y() + 430),
        QPointF(r.x() + 60, r.y() + 430), QPointF(r.x() + 60, r.y() + 60)]
lasso.press(poly[0], .5, 0)
for q in poly[1:]:
    lasso.move(q, .5, 1)
lasso.release(poly[-1], .5, 2)
c.ruler.toggle()
w.toolbar.buttons["lasso"].setChecked(True)
w.toolbar.set_checked("ruler", False)
save(w, "lasso.png")

# 5. Accueil
w2 = MainWindow(cfg)
w2.resize(1366, 840)
w2.show()
w2.vault_dock.show()
save(w2, "accueil.png")

for name in ("note.png", "menu.png", "pdf.png", "regle.png", "lasso.png", "accueil.png"):
    img = QImage(str(OUT / name))
    print(name, img.width(), "×", img.height())
shutil.rmtree(tmp, ignore_errors=True)
