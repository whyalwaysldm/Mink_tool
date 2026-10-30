"""
Đường tròn tiếp xúc với 2 đường thẳng và 1 đường tròn (bài toán Apollonius LLC).

Đoạn / tia được coi là đường thẳng chứa nó. Tâm X, bán kính r thỏa:
    n1·X = d1 + s1·r ,  n2·X = d2 + s2·r ,  |X − c| = |R + s3·r|
với s1, s2, s3 = ±1 → tối đa 8 đường tròn.
"""
import math
from itertools import product
from PyQt6.QtCore import QPointF

_EPS = 1e-9


def _line_form(curve: tuple):
    """(nx, ny, d): pháp tuyến đơn vị và hằng số của đường thẳng; None nếu suy biến."""
    a, b = curve[1], curve[2]
    dx, dy = b.x() - a.x(), b.y() - a.y()
    L = math.hypot(dx, dy)
    if L < _EPS:
        return None
    nx, ny = -dy / L, dx / L
    return nx, ny, nx * a.x() + ny * a.y()


def _quadratic(a: float, b: float, c: float) -> list:
    """Nghiệm thực của a·x² + b·x + c = 0 (a ≈ 0 → phương trình bậc nhất)."""
    if abs(a) < 1e-12:
        return [-c / b] if abs(b) > 1e-12 else []
    disc = b * b - 4 * a * c
    if disc < 0:
        if disc < -1e-7 * max(b * b, 1.0):
            return []
        disc = 0.0
    root = math.sqrt(disc)
    return [(-b - root) / (2 * a), (-b + root) / (2 * a)]


def _parallel(l1, l2, cx, cy, R) -> list:
    """Hai đường song song: r = nửa khoảng cách, tâm trên đường trung bình."""
    n1x, n1y, d1 = l1
    n2x, n2y, d2 = l2
    if n1x * n2x + n1y * n2y < 0:
        d2 = -d2
    r = abs(d1 - d2) / 2
    if r < _EPS:
        return []
    mid = (d1 + d2) / 2
    # X = P + t·u, P là chân vuông góc của c lên đường trung bình
    h = mid - (n1x * cx + n1y * cy)
    px, py = cx + n1x * h, cy + n1y * h
    ux, uy = -n1y, n1x
    out = []
    for s3 in (1, -1):
        d = R + s3 * r
        rest = d * d - h * h
        if rest < -1e-7:
            continue
        t = math.sqrt(max(rest, 0.0))
        out += [(px + ux * t, py + uy * t, r), (px - ux * t, py - uy * t, r)]
    return out


def _general(l1, l2, cx, cy, R) -> list:
    n1x, n1y, d1 = l1
    n2x, n2y, d2 = l2
    det = n1x * n2y - n1y * n2x
    out = []
    for s1, s2, s3 in product((1, -1), repeat=3):
        # X = P + r·Q từ 2 phương trình đường thẳng
        px = (d1 * n2y - d2 * n1y) / det
        py = (n1x * d2 - n2x * d1) / det
        qx = (s1 * n2y - s2 * n1y) / det
        qy = (n1x * s2 - n2x * s1) / det
        fx, fy = px - cx, py - cy
        a = qx * qx + qy * qy - 1.0
        b = 2 * (qx * fx + qy * fy - s3 * R)
        c = fx * fx + fy * fy - R * R
        for r in _quadratic(a, b, c):
            if r > 1e-6:
                out.append((px + qx * r, py + qy * r, r))
    return out


def tangent_circles(line1: tuple, line2: tuple, circle: tuple) -> list:
    """Mọi đường tròn tiếp xúc, dạng [(QPointF tâm, r)], không trùng nhau."""
    l1, l2 = _line_form(line1), _line_form(line2)
    if l1 is None or l2 is None:
        return []
    c, R = circle[1], circle[2]
    if abs(l1[0] * l2[1] - l1[1] * l2[0]) < 1e-7:
        raw = _parallel(l1, l2, c.x(), c.y(), R)
    else:
        raw = _general(l1, l2, c.x(), c.y(), R)
    result = []
    for x, y, r in raw:
        if any(math.hypot(x - q[0], y - q[1]) + abs(r - q[2]) < 1e-4
               for q in result):
            continue
        result.append((x, y, r))
    return [(QPointF(x, y), r) for x, y, r in result]
