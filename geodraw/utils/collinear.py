"""
Phát hiện điểm thẳng hàng và tự động tạo đoạn thẳng.

Dùng bởi:
  - LineTool  : sau khi vẽ đường thẳng AB → tạo đoạn AB nếu chưa có
  - PointTool : sau khi đặt điểm P trên đường/đoạn → tạo đoạn từ P tới
                các điểm cùng đường
"""

import math
from PyQt6.QtCore import QPointF

_TOL = 1.5   # px — khoảng cách vuông góc tối đa để coi là "trên đường"


# ── Hình học cơ bản ──────────────────────────────────────────────────────────

def _line_params(sp1: QPointF, sp2: QPointF):
    """(dx, dy, length, len_sq) hoặc None nếu 2 điểm trùng."""
    dx, dy = sp2.x() - sp1.x(), sp2.y() - sp1.y()
    len_sq  = dx * dx + dy * dy
    length  = math.sqrt(len_sq)
    return (dx, dy, length, len_sq) if length > 1e-6 else None


def _perp_dist(sp: QPointF, sp1: QPointF,
               dx: float, dy: float, length: float) -> float:
    return abs((sp.x() - sp1.x()) * dy - (sp.y() - sp1.y()) * dx) / length


def _param_t(sp: QPointF, sp1: QPointF,
             dx: float, dy: float, len_sq: float) -> float:
    return ((sp.x() - sp1.x()) * dx + (sp.y() - sp1.y()) * dy) / len_sq


# ── Tập hợp điểm nằm trên đường / đoạn / tia ────────────────────────────────

def points_on_infinite_line(scene, sp1: QPointF, sp2: QPointF) -> list:
    """Tất cả PointItem thẳng hàng với đường thẳng vô hạn qua sp1→sp2."""
    p = _line_params(sp1, sp2)
    if p is None:
        return []
    dx, dy, length, _ = p
    return [pt for pt in scene.point_items()
            if _perp_dist(pt.scenePos(), sp1, dx, dy, length) <= _TOL]


def points_on_segment_range(scene, sp1: QPointF, sp2: QPointF) -> list:
    """Tất cả PointItem nằm TRÊN đoạn sp1→sp2 (kể cả 2 đầu mút)."""
    p = _line_params(sp1, sp2)
    if p is None:
        return []
    dx, dy, length, len_sq = p
    eps = _TOL / length
    result = []
    for pt in scene.point_items():
        sp = pt.scenePos()
        if _perp_dist(sp, sp1, dx, dy, length) > _TOL:
            continue
        t = _param_t(sp, sp1, dx, dy, len_sq)
        if -eps <= t <= 1 + eps:
            result.append(pt)
    return result


def points_on_ray_range(scene, sp1: QPointF, sp2: QPointF) -> list:
    """Tất cả PointItem nằm trên tia xuất phát từ sp1 qua sp2."""
    p = _line_params(sp1, sp2)
    if p is None:
        return []
    dx, dy, length, len_sq = p
    eps = _TOL / length
    result = []
    for pt in scene.point_items():
        sp = pt.scenePos()
        if _perp_dist(sp, sp1, dx, dy, length) > _TOL:
            continue
        t = _param_t(sp, sp1, dx, dy, len_sq)
        if t >= -eps:
            result.append(pt)
    return result


# ── Kiểm tra đoạn đã tồn tại ─────────────────────────────────────────────────

def segment_exists(scene, pa, pb) -> bool:
    """True nếu scene đã có SegmentItem nối pa ↔ pb."""
    from items.segment import SegmentItem
    for item in scene.items():
        if isinstance(item, SegmentItem):
            if (item.p1 is pa and item.p2 is pb) or \
               (item.p1 is pb and item.p2 is pa):
                return True
    return False


# ── Tạo đoạn thẳng thiếu ────────────────────────────────────────────────────

def _make_segments(scene, new_pt, collinear_pts: list) -> list:
    """Tạo SegmentItem từ new_pt đến mỗi điểm trong collinear_pts (nếu chưa có).
    Các segment đã được addItem vào scene. Trả về list đã tạo."""
    from items.segment import SegmentItem
    created = []
    for other in collinear_pts:
        if other is new_pt:
            continue
        if not segment_exists(scene, new_pt, other):
            seg = SegmentItem(new_pt, other)
            scene.addItem(seg)
            created.append(seg)
    return created


def auto_segments_for_new_point(scene, new_pt) -> list:
    """
    Sau khi thêm new_pt vào scene, quét tất cả LineItem / RayItem / SegmentItem.
    Với mỗi item mà new_pt nằm trên, tạo các SegmentItem còn thiếu đến
    các điểm cùng đường/đoạn.

    Trả về list SegmentItem đã tạo (đã được addItem, chờ ghi vào history).
    """
    from items.line import LineItem, RayItem
    from items.segment import SegmentItem

    created  = []
    # frozenset(id) để tránh xử lý 2 lần cùng một nhóm điểm thẳng hàng
    processed = set()

    for item in list(scene.items()):
        if not (hasattr(item, 'p1') and hasattr(item, 'p2')):
            continue
        sp1 = item.p1.scenePos()
        sp2 = item.p2.scenePos()

        if isinstance(item, LineItem):
            pts = points_on_infinite_line(scene, sp1, sp2)
        elif isinstance(item, RayItem):
            pts = points_on_ray_range(scene, sp1, sp2)
        elif isinstance(item, SegmentItem):
            pts = points_on_segment_range(scene, sp1, sp2)
        else:
            continue

        if new_pt not in pts:
            continue

        # Tránh xử lý lại nếu LineItem và SegmentItem cùng hướng
        key = frozenset(id(p) for p in pts)
        if key in processed:
            continue
        processed.add(key)

        created += _make_segments(scene, new_pt, pts)

    return created
