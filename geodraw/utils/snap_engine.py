"""
Snap engine nâng cao:
  1. Ưu tiên cao nhất : PointItem có sẵn gần con trỏ          → "point"
  2. Thứ hai          : giao điểm của 2 đường đã vẽ           → "intersection"
  3. Thứ ba           : điểm gần nhất trên đường / đoạn / tia → "on_curve"
  4. Fallback         : vị trí con trỏ tự do                  → "free"

Dùng qua  scene.snap()  (backward-compat) hoặc  scene.snap_info()
để lấy thêm snap_type cho hiệu ứng highlight.
"""
import math
from PyQt6.QtCore import QPointF
from .geometry import distance
from . import intersections as I

SNAP_RADIUS    = 14.0   # pixel scene — vùng nhận snap điểm / giao điểm
ON_CURVE_DIST  = 12.0   # px — khoảng cách vuông góc tối đa để snap lên đường


# ── Kết quả snap ─────────────────────────────────────────────────────────────

class SnapResult:
    """
    item       – PointItem nếu snap vào điểm có sẵn, None nếu giao điểm/tự do
    pos        – vị trí snap chính xác
    snap_type  – "point" | "intersection" | "on_curve" | "free"
    host       – (chỉ với "on_curve") đối tượng chứa điểm snap
    host_idx   – chỉ số curve trong curves_of(host) (cạnh đa giác…)
    """
    __slots__ = ("item", "pos", "snap_type", "host", "host_idx")

    def __init__(self, item, pos: QPointF, snap_type: str,
                 host=None, host_idx: int = 0):
        self.item      = item
        self.pos       = pos
        self.snap_type = snap_type
        self.host      = host
        self.host_idx  = host_idx


# ── Hàm chính ────────────────────────────────────────────────────────────────

def snap(pos: QPointF, scene, exclude=None) -> SnapResult:
    """Trả về SnapResult tốt nhất cho vị trí pos trong scene."""

    # ── 1. Điểm có sẵn (ưu tiên cao nhất) ───────────────────────────────
    from items.point import PointItem
    best_item = None
    best_d    = SNAP_RADIUS
    for item in scene.items():
        if not isinstance(item, PointItem):
            continue
        if item is exclude or not item.isVisible():
            continue
        d = distance(pos, item.scenePos())
        if d < best_d:
            best_d    = d
            best_item = item
    if best_item is not None:
        return SnapResult(best_item, best_item.scenePos(), "point")

    # Thu thập đường một lần, dùng cho cả giao điểm lẫn on_curve
    curves, hosts = _collect_curves(scene)

    # ── 2. Giao điểm của các đường đã vẽ ────────────────────────────────
    best_ipt = None
    best_d   = SNAP_RADIUS
    n = len(curves)
    for i in range(n):
        for j in range(i + 1, n):
            for pt in _intersect(curves[i], curves[j]):
                d = distance(pos, pt)
                if d < best_d:
                    best_d   = d
                    best_ipt = pt
    if best_ipt is not None:
        return SnapResult(None, best_ipt, "intersection")

    # ── 3. Điểm gần nhất trên đường / đoạn / tia / đường tròn ──────────
    best_foot = None
    best_host = (None, 0)
    best_d    = ON_CURVE_DIST          # dùng khoảng cách vuông góc
    for curve, host in zip(curves, hosts):
        foot = _nearest_on_curve(pos, curve)
        if foot is not None:
            d = distance(pos, foot)
            if d < best_d:
                best_d    = d
                best_foot = foot
                best_host = host
    if best_foot is not None:
        return SnapResult(None, best_foot, "on_curve", *best_host)

    # ── 4. Tự do ─────────────────────────────────────────────────────────
    return SnapResult(None, pos, "free")


# ── Thu thập các đường trong scene ───────────────────────────────────────────
# Mỗi "curve" là một tuple: ('segment'|'line'|'ray', p1, p2)
#                       hoặc ('circle', center_QPointF, radius_float)

def _collect_curves(scene) -> tuple:
    """(curves, hosts) — hosts[i] = (item, chỉ số curve trong curves_of(item))."""
    curves, hosts = [], []
    for item in scene.items():
        for k, c in enumerate(curves_of(item)):
            curves.append(c)
            hosts.append((item, k))
    return curves, hosts


def curves_of(item) -> list:
    """Các curve của một đối tượng (rỗng nếu không phải đường)."""
    from items.segment import SegmentItem
    from items.line import LineItem, RayItem
    from items.circle import CircleItem
    from items.circumcircle import CircumcircleItem
    from items.polygon import PolygonItem
    from items.fixed_polygon import FixedPolygonItem
    from items.arc import ArcItem
    from items.bisector_ray import BisectorRayItem   # tia phân giác

    curves = []
    if isinstance(item, SegmentItem):
        curves.append(('segment', item.p1.scenePos(), item.p2.scenePos()))

    elif isinstance(item, RayItem):          # phải trước LineItem
        curves.append(('ray', item.p1.scenePos(), item.p2.scenePos()))

    elif isinstance(item, LineItem):
        curves.append(('line', item.p1.scenePos(), item.p2.scenePos()))

    elif isinstance(item, CircleItem):
        c = item.center_pt.scenePos()
        r = item._radius()
        if r > 0.5:
            curves.append(('circle', c, r))

    elif isinstance(item, CircumcircleItem):
        c, r = item._data()
        if c is not None and r > 0.5:
            curves.append(('circle', c, r))

    elif isinstance(item, ArcItem):
        # Dùng toàn bộ đường tròn chứa cung (đủ cho snap)
        c, r = item._circle_from_3pts(
            item.p_start.scenePos(),
            item.p_mid.scenePos(),
            item.p_end.scenePos())
        if c is not None and r > 0.5:
            curves.append(('circle', c, r))

    elif isinstance(item, BisectorRayItem):
        v = item._vertex.scenePos()
        d = item._bisector_dir()
        # Biểu diễn tia phân giác dưới dạng ('ray', origin, p2)
        curves.append(('ray', v,
                       QPointF(v.x() + d.x(), v.y() + d.y())))

    elif isinstance(item, PolygonItem):
        pts = [p.scenePos() for p in item.points]
        _add_poly_edges(curves, pts, item.closed)

    elif isinstance(item, FixedPolygonItem):
        pts = [item.mapToScene(p) for p in item._points]
        _add_poly_edges(curves, pts, closed=True)

    return curves


def _nearest_on_curve(pos: QPointF, curve: tuple) -> "QPointF | None":
    """
    Trả về điểm gần nhất trên curve với pos (chiếu vuông góc hoặc điểm trên vòng tròn).
    Trả về None nếu khoảng cách > ON_CURVE_DIST.
    """
    t = curve[0]

    if t in ('segment', 'line', 'ray'):
        p1, p2 = curve[1], curve[2]
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        len_sq = dx * dx + dy * dy
        if len_sq < 1e-12:
            return None
        # Tham số t: vị trí chiếu trên đường
        param = ((pos.x() - p1.x()) * dx +
                 (pos.y() - p1.y()) * dy) / len_sq
        if t == 'segment':
            param = max(0.0, min(1.0, param))
        elif t == 'ray':
            param = max(0.0, param)
        # 'line': param không bị clamp
        foot = QPointF(p1.x() + param * dx, p1.y() + param * dy)
        return foot if distance(pos, foot) <= ON_CURVE_DIST else None

    elif t == 'circle':
        center, radius = curve[1], curve[2]
        dx = pos.x() - center.x()
        dy = pos.y() - center.y()
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < 1e-9:
            return None
        foot = QPointF(center.x() + dx / dist * radius,
                       center.y() + dy / dist * radius)
        return foot if distance(pos, foot) <= ON_CURVE_DIST else None

    return None


def _add_poly_edges(curves: list, pts: list, closed: bool):
    n = len(pts)
    if n < 2:
        return
    limit = n if closed else n - 1
    for i in range(limit):
        curves.append(('segment', pts[i], pts[(i + 1) % n]))


# ── Tính giao điểm giữa 2 đường ──────────────────────────────────────────────

def _intersect(c1: tuple, c2: tuple) -> list:
    t1, d1a, d1b = c1
    t2, d2a, d2b = c2

    # line × line
    if t1 == 'line' and t2 == 'line':
        pt = I.line_line(d1a, d1b, d2a, d2b)
        return [pt] if pt else []

    # line × segment  (cả 2 chiều)
    if t1 == 'line' and t2 == 'segment':
        pt = I.line_segment(d1a, d1b, d2a, d2b)
        return [pt] if pt else []
    if t1 == 'segment' and t2 == 'line':
        pt = I.line_segment(d2a, d2b, d1a, d1b)
        return [pt] if pt else []

    # line × ray
    if t1 == 'line' and t2 == 'ray':
        pt = I.ray_line(d2a, d2b, d1a, d1b)
        return [pt] if pt else []
    if t1 == 'ray' and t2 == 'line':
        pt = I.ray_line(d1a, d1b, d2a, d2b)
        return [pt] if pt else []

    # segment × segment
    if t1 == 'segment' and t2 == 'segment':
        pt = I.segment_segment(d1a, d1b, d2a, d2b)
        return [pt] if pt else []

    # segment × ray
    if t1 == 'segment' and t2 == 'ray':
        pt = I.ray_segment(d2a, d2b, d1a, d1b)
        return [pt] if pt else []
    if t1 == 'ray' and t2 == 'segment':
        pt = I.ray_segment(d1a, d1b, d2a, d2b)
        return [pt] if pt else []

    # ray × ray
    if t1 == 'ray' and t2 == 'ray':
        pt = I.ray_ray(d1a, d1b, d2a, d2b)
        return [pt] if pt else []

    # circle × circle
    if t1 == 'circle' and t2 == 'circle':
        return I.circle_circle(d1a, d1b, d2a, d2b)

    # circle × line
    if t1 == 'circle' and t2 == 'line':
        return I.circle_line(d1a.x(), d1a.y(), d1b, d2a, d2b)
    if t1 == 'line' and t2 == 'circle':
        return I.circle_line(d2a.x(), d2a.y(), d2b, d1a, d1b)

    # circle × segment
    if t1 == 'circle' and t2 == 'segment':
        return I.circle_segment(d1a.x(), d1a.y(), d1b, d2a, d2b)
    if t1 == 'segment' and t2 == 'circle':
        return I.circle_segment(d2a.x(), d2a.y(), d2b, d1a, d1b)

    # circle × ray
    if t1 == 'circle' and t2 == 'ray':
        return I.circle_ray(d1a.x(), d1a.y(), d1b, d2a, d2b)
    if t1 == 'ray' and t2 == 'circle':
        return I.circle_ray(d2a.x(), d2a.y(), d2b, d1a, d1b)

    return []
