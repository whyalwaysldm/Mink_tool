import math
from PyQt6.QtCore import QPointF

SNAP_RADIUS = 12.0


def distance(p1: QPointF, p2: QPointF) -> float:
    dx = p1.x() - p2.x()
    dy = p1.y() - p2.y()
    return math.sqrt(dx * dx + dy * dy)


def snap_to_point(pos: QPointF, candidates: list) -> tuple:
    """Return (PointItem, snapped_pos) or (None, pos) if no snap."""
    best = None
    best_d = SNAP_RADIUS
    for item in candidates:
        d = distance(pos, item.center())
        if d < best_d:
            best_d = d
            best = item
    if best is not None:
        return best, best.center()
    return None, pos


def perpendicular_offset(p: QPointF, half_w: float, direction: QPointF) -> tuple:
    """Return two points offset perpendicular to direction by half_w."""
    length = math.sqrt(direction.x()**2 + direction.y()**2)
    if length < 1e-9:
        return QPointF(p.x(), p.y() - half_w), QPointF(p.x(), p.y() + half_w)
    nx = -direction.y() / length
    ny = direction.x() / length
    return (QPointF(p.x() + nx * half_w, p.y() + ny * half_w),
            QPointF(p.x() - nx * half_w, p.y() - ny * half_w))


def catmull_rom_to_bezier(p0: QPointF, p1: QPointF,
                           p2: QPointF, p3: QPointF) -> tuple:
    """Convert one Catmull-Rom segment to cubic bezier control points."""
    cp1 = QPointF(p1.x() + (p2.x() - p0.x()) / 6,
                  p1.y() + (p2.y() - p0.y()) / 6)
    cp2 = QPointF(p2.x() - (p3.x() - p1.x()) / 6,
                  p2.y() - (p3.y() - p1.y()) / 6)
    return cp1, cp2
