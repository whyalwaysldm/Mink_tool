"""
Tính giao điểm giữa các đường hình học thuần tuý.
Tất cả tham số và kết quả đều dùng QPointF (toạ độ scene).
"""
import math
from PyQt6.QtCore import QPointF

_EPS = 1e-10


# ── helpers ──────────────────────────────────────────────────────────────────

def _cross2d(ax: float, ay: float, bx: float, by: float) -> float:
    return ax * by - ay * bx


# ── Line / Segment / Ray ──────────────────────────────────────────────────────

def line_line(p1: QPointF, p2: QPointF,
              q1: QPointF, q2: QPointF) -> "QPointF | None":
    """Giao điểm 2 đường thẳng vô hạn. None nếu song song."""
    dx1 = p2.x() - p1.x();  dy1 = p2.y() - p1.y()
    dx2 = q2.x() - q1.x();  dy2 = q2.y() - q1.y()
    denom = _cross2d(dx1, dy1, dx2, dy2)
    if abs(denom) < _EPS:
        return None
    t = _cross2d(q1.x() - p1.x(), q1.y() - p1.y(), dx2, dy2) / denom
    return QPointF(p1.x() + t * dx1, p1.y() + t * dy1)


def segment_segment(a1: QPointF, a2: QPointF,
                    b1: QPointF, b2: QPointF) -> "QPointF | None":
    """Giao điểm 2 đoạn thẳng. None nếu không cắt nhau."""
    dx1 = a2.x() - a1.x();  dy1 = a2.y() - a1.y()
    dx2 = b2.x() - b1.x();  dy2 = b2.y() - b1.y()
    denom = _cross2d(dx1, dy1, dx2, dy2)
    if abs(denom) < _EPS:
        return None
    fx = b1.x() - a1.x();   fy = b1.y() - a1.y()
    t = _cross2d(fx, fy, dx2, dy2) / denom
    u = _cross2d(fx, fy, dx1, dy1) / denom
    if -_EPS <= t <= 1 + _EPS and -_EPS <= u <= 1 + _EPS:
        return QPointF(a1.x() + t * dx1, a1.y() + t * dy1)
    return None


def line_segment(lp1: QPointF, lp2: QPointF,
                 sp1: QPointF, sp2: QPointF) -> "QPointF | None":
    """Đường thẳng vô hạn lp1-lp2 cắt đoạn sp1-sp2."""
    dx1 = lp2.x() - lp1.x(); dy1 = lp2.y() - lp1.y()
    dx2 = sp2.x() - sp1.x(); dy2 = sp2.y() - sp1.y()
    denom = _cross2d(dx1, dy1, dx2, dy2)
    if abs(denom) < _EPS:
        return None
    # u là tham số trên đoạn sp — cross(sp1-lp1, d_line) / denom
    u = _cross2d(sp1.x() - lp1.x(), sp1.y() - lp1.y(), dx1, dy1) / denom
    if -_EPS <= u <= 1 + _EPS:
        return QPointF(sp1.x() + u * dx2, sp1.y() + u * dy2)
    return None


def ray_line(rp1: QPointF, rp2: QPointF,
             lp1: QPointF, lp2: QPointF) -> "QPointF | None":
    """Tia từ rp1 qua rp2, cắt đường thẳng vô hạn lp1-lp2."""
    dx1 = rp2.x() - rp1.x(); dy1 = rp2.y() - rp1.y()
    dx2 = lp2.x() - lp1.x(); dy2 = lp2.y() - lp1.y()
    denom = _cross2d(dx1, dy1, dx2, dy2)
    if abs(denom) < _EPS:
        return None
    t = _cross2d(lp1.x() - rp1.x(), lp1.y() - rp1.y(), dx2, dy2) / denom
    if t >= -_EPS:
        return QPointF(rp1.x() + t * dx1, rp1.y() + t * dy1)
    return None


def ray_segment(rp1: QPointF, rp2: QPointF,
                sp1: QPointF, sp2: QPointF) -> "QPointF | None":
    """Tia từ rp1 qua rp2, cắt đoạn sp1-sp2."""
    dx1 = rp2.x() - rp1.x(); dy1 = rp2.y() - rp1.y()
    dx2 = sp2.x() - sp1.x(); dy2 = sp2.y() - sp1.y()
    denom = _cross2d(dx1, dy1, dx2, dy2)
    if abs(denom) < _EPS:
        return None
    fx = sp1.x() - rp1.x(); fy = sp1.y() - rp1.y()
    t = _cross2d(fx, fy, dx2, dy2) / denom
    u = _cross2d(fx, fy, dx1, dy1) / denom
    if t >= -_EPS and -_EPS <= u <= 1 + _EPS:
        return QPointF(rp1.x() + t * dx1, rp1.y() + t * dy1)
    return None


def ray_ray(r1p1: QPointF, r1p2: QPointF,
            r2p1: QPointF, r2p2: QPointF) -> "QPointF | None":
    """Giao điểm 2 tia, chỉ lấy phần nằm trên cả 2 tia (t >= 0, u >= 0)."""
    dx1 = r1p2.x() - r1p1.x(); dy1 = r1p2.y() - r1p1.y()
    dx2 = r2p2.x() - r2p1.x(); dy2 = r2p2.y() - r2p1.y()
    denom = _cross2d(dx1, dy1, dx2, dy2)
    if abs(denom) < _EPS:
        return None
    fx = r2p1.x() - r1p1.x(); fy = r2p1.y() - r1p1.y()
    t = _cross2d(fx, fy, dx2, dy2) / denom
    u = _cross2d(fx, fy, dx1, dy1) / denom
    if t >= -_EPS and u >= -_EPS:
        return QPointF(r1p1.x() + t * dx1, r1p1.y() + t * dy1)
    return None


# ── Circle ────────────────────────────────────────────────────────────────────

def _circle_line_ts(cx: float, cy: float, r: float,
                    lp1: QPointF, lp2: QPointF) -> list:
    """Tham số t của giao điểm đường thẳng vô hạn với đường tròn."""
    dx = lp2.x() - lp1.x(); dy = lp2.y() - lp1.y()
    fx = lp1.x() - cx;      fy = lp1.y() - cy
    a = dx * dx + dy * dy
    if a < _EPS:
        return []
    b = 2 * (fx * dx + fy * dy)
    c = fx * fx + fy * fy - r * r
    disc = b * b - 4 * a * c
    if disc < 0:
        return []
    sq = math.sqrt(max(0.0, disc))
    return [(-b - sq) / (2 * a), (-b + sq) / (2 * a)]


def circle_line(cx: float, cy: float, r: float,
                lp1: QPointF, lp2: QPointF) -> list:
    """0, 1 hoặc 2 giao điểm giữa đường tròn và đường thẳng vô hạn."""
    dx = lp2.x() - lp1.x(); dy = lp2.y() - lp1.y()
    return [QPointF(lp1.x() + t * dx, lp1.y() + t * dy)
            for t in _circle_line_ts(cx, cy, r, lp1, lp2)]


def circle_segment(cx: float, cy: float, r: float,
                   sp1: QPointF, sp2: QPointF) -> list:
    """Giao điểm đường tròn với đoạn thẳng."""
    dx = sp2.x() - sp1.x(); dy = sp2.y() - sp1.y()
    return [QPointF(sp1.x() + t * dx, sp1.y() + t * dy)
            for t in _circle_line_ts(cx, cy, r, sp1, sp2)
            if -_EPS <= t <= 1 + _EPS]


def circle_ray(cx: float, cy: float, r: float,
               rp1: QPointF, rp2: QPointF) -> list:
    """Giao điểm đường tròn với tia."""
    dx = rp2.x() - rp1.x(); dy = rp2.y() - rp1.y()
    return [QPointF(rp1.x() + t * dx, rp1.y() + t * dy)
            for t in _circle_line_ts(cx, cy, r, rp1, rp2)
            if t >= -_EPS]


def circle_circle(c1: QPointF, r1: float,
                  c2: QPointF, r2: float) -> list:
    """0, 1 hoặc 2 giao điểm giữa 2 đường tròn."""
    dx = c2.x() - c1.x(); dy = c2.y() - c1.y()
    d = math.sqrt(dx * dx + dy * dy)
    if d < _EPS:
        return []
    if d > r1 + r2 + _EPS or d < abs(r1 - r2) - _EPS:
        return []
    a = (r1 * r1 - r2 * r2 + d * d) / (2 * d)
    h2 = r1 * r1 - a * a
    if h2 < 0:
        return []
    h = math.sqrt(max(0.0, h2))
    mx = c1.x() + a * dx / d
    my = c1.y() + a * dy / d
    if h < _EPS:
        return [QPointF(mx, my)]
    return [QPointF(mx + h * dy / d, my - h * dx / d),
            QPointF(mx - h * dy / d, my + h * dx / d)]
