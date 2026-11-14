import math

import numpy as np
import pytest

from plume.engine.shape_recognition import recognize

rng = np.random.default_rng(42)


def pts(xy, noise=1.0):
    xy = np.asarray(xy, float) + rng.normal(0, noise, (len(xy), 2))
    return [(x, y, 0.5, i) for i, (x, y) in enumerate(xy)]


def polyline(vertices, per_edge=25, close=False):
    v = list(vertices) + ([vertices[0]] if close else [])
    out = []
    for a, b in zip(v, v[1:]):
        for t in np.linspace(0, 1, per_edge, endpoint=False):
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    out.append(v[-1])
    return out


def test_line_snaps_horizontal():
    kind, g = recognize(pts(polyline([(0, 0), (200, 6)])))
    assert kind == "line"
    assert abs(g[0][1] - g[1][1]) < 1e-6  # aimantée à l'horizontale


def test_diagonal_line():
    kind, g = recognize(pts(polyline([(0, 0), (150, 100)])))
    assert kind == "line"


@pytest.mark.parametrize("w,h", [(200, 120), (100, 100)])
def test_rectangle(w, h):
    kind, g = recognize(pts(polyline([(0, 0), (w, 0), (w, h), (0, h)], close=True)))
    assert kind == "rect" and len(g) == 4
    xs, ys = sorted(p[0] for p in g), sorted(p[1] for p in g)
    assert abs((xs[-1] - xs[0]) - w) < 6 and abs((ys[-1] - ys[0]) - h) < 6
    assert abs(g[0][1] - g[1][1]) < 1e-6  # côté du haut horizontal


def test_circle_and_ellipse():
    a = np.linspace(0, 2 * math.pi, 120)
    kind, g = recognize(pts(np.column_stack([100 + 60 * np.cos(a), 100 + 60 * np.sin(a)])))
    assert kind == "ellipse"
    w, h = math.dist(g[0], g[1]), math.dist(g[0], g[3])
    assert abs(w - h) < 1e-6 and 110 < w < 130  # cercle parfait
    kind, g = recognize(pts(np.column_stack([100 + 90 * np.cos(a), 100 + 40 * np.sin(a)])))
    assert kind == "ellipse" and math.dist(g[0], g[1]) > 1.8 * math.dist(g[0], g[3])


def test_triangle():
    kind, g = recognize(pts(polyline([(0, 100), (60, 0), (120, 100)], close=True)))
    assert kind == "triangle" and len(g) == 3


def test_arrow():
    shaft = polyline([(0, 0), (200, 0)], per_edge=60)
    head = polyline([(200, 0), (175, -18), (200, 0), (175, 18)], per_edge=10)
    kind, g = recognize(pts(shaft + head[1:], noise=0.6))
    assert kind == "arrow" and abs(g[1][0] - 200) < 5


def test_scribble_and_tiny_rejected():
    zig = [(i * 3, (i % 2) * 40 + rng.normal(0, 8)) for i in range(60)]
    assert recognize(pts(zig, 0)) is None
    assert recognize(pts([(0, 0), (1, 1), (2, 1), (2, 2), (3, 3)], 0)) is None


def _start_mid_edge(vertices, per_edge=25):
    """Forme fermée commencée au milieu du premier côté, avec léger dépassement à la fin."""
    ring = polyline(vertices, per_edge, close=True)
    half = per_edge // 2
    return ring[half:] + ring[1:half + 4]


@pytest.mark.parametrize("vertices,kind", [
    ([(0, 0), (200, 0), (200, 120), (0, 120)], "rect"),
    ([(0, 100), (60, 0), (120, 100)], "triangle"),
    ([(100, 0), (200, 100), (100, 200), (0, 100)], "rect"),  # carré posé sur la pointe
    ([(100, 0), (180, 120), (100, 240), (20, 120)], "polygon"),  # losange
])
def test_closed_shape_started_mid_edge(vertices, kind):
    got = recognize(pts(_start_mid_edge(vertices), noise=1.2))
    assert got is not None and got[0] == kind


@pytest.mark.parametrize("n", [5, 6])
def test_regular_polygons(n):
    a = [2 * math.pi * k / n - math.pi / 2 for k in range(n)]
    v = [(150 + 100 * math.cos(t), 150 + 100 * math.sin(t)) for t in a]
    kind, g = recognize(pts(polyline(v, close=True), noise=1.0))
    assert kind == "polygon" and len(g) == n


def test_robustness_hand_drawn():
    """Formes tremblées, départ n'importe où : au moins 9 sur 10 reconnues correctement."""
    ok = total = 0
    for trial in range(40):
        for vertices, kind in (([(0, 0), (180, 0), (180, 110), (0, 110)], "rect"),
                               ([(0, 100), (70, 0), (140, 100)], "triangle")):
            ring = polyline(vertices, 30, close=True)
            start = int(rng.integers(0, len(ring) - 1))
            stroke = ring[start:] + ring[1:start + 1]
            got = recognize(pts(stroke, noise=1.8))
            total += 1
            ok += got is not None and got[0] == kind
        a = np.linspace(0, 2 * math.pi * 1.04, 120) + rng.uniform(0, 2 * math.pi)
        got = recognize(pts(np.column_stack([90 * np.cos(a), 60 * np.sin(a)]), noise=1.8))
        total += 1
        ok += got is not None and got[0] == "ellipse"
    assert ok / total >= 0.9, f"{ok}/{total}"
