import math

import numpy as np

from plume.engine import transform as tf
from plume.model.document import Page
from plume.model.elements import ImageItem, Shape, Stroke


def stroke(x0=0.0):
    return Stroke(points=[(x0, 0, .5, 0), (x0 + 10, 0, .5, 1)], width=2)


def test_translate_and_scale_stroke_keeps_id():
    s = stroke()
    t = tf.transform_element(s, tf.translate(5, 7))
    assert t.id == s.id and t.points[0][:2] == (5, 7) and t.points[0][2:] == s.points[0][2:]
    big = tf.transform_element(s, tf.scale_about(0, 0, 2, 2))
    assert big.points[1][:2] == (20, 0) and math.isclose(big.width, 4)


def test_rotate_around_center():
    s = stroke()
    r = tf.transform_element(s, tf.rotate_about(5, 0, 90))
    xs = [p[0] for p in r.points]
    ys = [p[1] for p in r.points]
    assert np.allclose(xs, [5, 5]) and np.allclose(sorted(ys), [-5, 5])


def test_image_rotation_and_scale():
    img = ImageItem(asset="assets/a.png", rect=(0, 0, 20, 10))
    r = tf.transform_element(img, tf.rotate_about(10, 5, 30))
    assert math.isclose(r.rotation, 30) and np.allclose(r.rect, (0, 0, 20, 10))
    s = tf.transform_element(img, tf.scale_about(0, 0, 2, 3))
    assert np.allclose(s.rect, (0, 0, 40, 30))


def test_shape_transform():
    sh = Shape(kind="rect", geometry=[(0, 0), (10, 0), (10, 10), (0, 10)], width=1)
    m = tf.transform_element(sh, tf.translate(1, 1))
    assert m.geometry[0] == (1, 1)


def test_new_id_copy_offset():
    s = stroke()
    c = tf.with_new_id(s, 10, 10)
    assert c.id != s.id and c.points[0][:2] == (10, 10)


def test_select_in_lasso():
    page = Page()
    inside, outside = stroke(0), stroke(100)
    page.add(inside)
    page.add(outside)
    lasso = [(-5, -5), (20, -5), (20, 5), (-5, 5)]
    assert tf.select_in_lasso(page, lasso) == [inside]
    assert tf.select_in_lasso(page, lasso[:2]) == []


def test_bounds():
    assert tf.bounds([stroke(0), stroke(100)]) == (-1, -1, 111, 1)
