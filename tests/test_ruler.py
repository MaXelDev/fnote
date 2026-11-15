import math

import pytest

from fnote.engine.ruler_geometry import RulerGeometry, normalize_deg, snap_angle


@pytest.mark.parametrize("deg,expected", [(1.5, 0), (14, 15), (44.0, 45), (91, 90), (37, 37), (-29, -30)])
def test_snap_angle(deg, expected):
    assert snap_angle(deg) == expected


def test_normalize():
    assert normalize_deg(180) == 0 and normalize_deg(270) == 90 and normalize_deg(-45) == -45


@pytest.mark.parametrize("angle", [0.0, 37.0, 90.0])
def test_edges_and_projection(angle):
    r = RulerGeometry(400, 300, angle, length=600, thickness=80)
    # point juste au-dessus du bord haut, au milieu de la règle
    x, y = r.to_screen(50, -40 - 5)
    assert r.edge_near(x, y) == -1
    px, py = r.project(x, y, -1)
    s, t = r.to_local(px, py)
    assert math.isclose(t, -40, abs_tol=1e-9) and math.isclose(s, 50, abs_tol=1e-9)
    # bord bas, avec décalage de la demi-épaisseur du trait
    x, y = r.to_screen(-100, 40 + 3)
    assert r.edge_near(x, y) == 1
    s, t = r.to_local(*r.project(x, y, 1, offset=2))
    assert math.isclose(t, 42, abs_tol=1e-9)


def test_far_or_inside_not_snapped():
    r = RulerGeometry(400, 300, 0, length=600, thickness=80)
    assert r.edge_near(400, 300) is None          # au milieu de la règle
    assert r.edge_near(400, 200) is None          # loin au-dessus
    assert r.edge_near(1000, 260) is None         # au-delà de l'extrémité
    assert r.contains(400, 300) and not r.contains(400, 200)
