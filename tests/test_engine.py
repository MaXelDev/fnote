import math

import numpy as np

from fnote.engine import geometry as g
from fnote.engine.pressure import PressureCurve
from fnote.engine.smoothing import StreamSmoother, finalize


def test_pressure_curve_monotone_and_bounded():
    c = PressureCurve([(0, 0.2), (0.5, 0.1), (1, 1)])  # point non monotone corrigé
    vals = c(np.linspace(-1, 2, 50))
    assert (np.diff(vals) >= 0).all()
    assert c(0.0) == 0.2 and c(1.0) == 1.0 and c(5.0) == 1.0


def test_sensitivity_preset():
    soft, firm = PressureCurve.from_sensitivity(1), PressureCurve.from_sensitivity(0)
    assert soft(0.3) > firm(0.3)


def test_stream_smoother_low_lag():
    s = StreamSmoother()
    out = [s.add((float(i), 0.0, 0.5, i)) for i in range(10)]
    # sur une droite à vitesse constante, le retard est < 1 échantillon
    assert all(i - o[0] < 1.0 for i, o in enumerate(out))
    assert out[0] == (0.0, 0.0, 0.5, 0)


def test_finalize_keeps_ends_and_reduces_noise():
    rng = np.random.default_rng(0)
    pts = [(float(i), float(rng.normal(0, 0.5)), 0.5, i) for i in range(50)]
    out = finalize(pts)
    assert out[0][:2] == pts[0][:2] and out[-1][:2] == pts[-1][:2]
    assert np.std([p[1] for p in out[1:-1]]) < np.std([p[1] for p in pts[1:-1]])


def test_widths_by_tool():
    c = PressureCurve()
    pts = [(0, 0, 0.1, 0), (1, 0, 1.0, 1)]
    w = g.widths(pts, 2.0, "fountain", c)
    assert w[0] < w[1] == 2.0
    assert (g.widths(pts, 2.0, "ballpoint", c) == 2.0).all()


def test_outline_closed_polygon_width():
    xy = np.array([[0, 0], [10, 0], [20, 0]], float)
    poly = g.outline(xy, np.array([2.0, 2.0, 2.0]))
    assert np.isclose(poly[:, 1].max(), 1.0) and np.isclose(poly[:, 1].min(), -1.0)
    assert poly[:, 0].min() < 0 and poly[:, 0].max() > 20  # extrémités arrondies
    dot = g.outline(np.array([[5, 5]], float), np.array([4.0]))
    assert np.allclose(np.linalg.norm(dot - [5, 5], axis=1), 2)


def test_fast_eraser_crossing_without_sample_inside():
    # trait horizontal avec 2 seuls échantillons ; la gomme le traverse verticalement
    xy = np.array([[0, 0], [100, 0]], float)
    assert g.polyline_hits_segment(xy, (50, -30), (50, 30), radius=1)
    assert not g.polyline_hits_segment(xy, (50, 10), (50, 30), radius=1)


def test_partial_eraser_splits_stroke():
    pts = [(0, 0, 0.5, 0), (100, 0, 0.5, 10)]
    pieces = g.split_by_eraser(pts, (50, -5), (50, 5), radius=3)
    assert len(pieces) == 2
    assert max(p[0] for p in pieces[0]) < 47 and min(p[0] for p in pieces[1]) > 53


def test_point_in_polygon():
    square = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], float)
    inside = g.point_in_polygon(np.array([[5, 5], [15, 5], [-1, -1]], float), square)
    assert inside.tolist() == [True, False, False]


def test_resample_max_gap():
    out = g.resample([(0, 0, 0, 0), (10, 0, 1, 10)], 1.0)
    gaps = [math.dist(a[:2], b[:2]) for a, b in zip(out, out[1:])]
    assert max(gaps) <= 1.0 + 1e-9 and out[-1] == (10, 0, 1, 10)
