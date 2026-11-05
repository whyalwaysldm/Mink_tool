"""
PointLabelItem — nhãn chữ gắn với một PointItem.

• Hiển thị tên điểm bằng font toán (Times New Roman italic).
• Tự đặt ở phía "bên ngoài" hình (ngược hướng các đường đi qua điểm).
• Kéo tự do bằng SelectTool / công cụ Nhãn, giữ trong vòng MAX_DIST px quanh điểm.
• Khi điểm di chuyển, nhãn theo cùng (giữ nguyên offset).
• Kéo điểm + nhãn cùng lúc → nhãn không bị constraint (offset giữ nguyên).
"""
import math
from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtGui import (QPainter, QPen, QBrush, QColor,
                          QFont, QFontMetricsF)
from PyQt6.QtCore import QRectF, QPointF, Qt
from .base import GeoItem
from .point import PointItem

MAX_DIST = 160.0  # px — xa nhất nhãn có thể cách tâm điểm
DEFAULT_FONT_SIZE = 9   # cỡ chữ tên điểm / tên đường
LABEL_GAP = 11.0  # px — khoảng cách từ điểm tới tâm chữ khi tự đặt
MIN_DIST =  7.0   # px — gần nhất (tránh đè lên dot điểm)


class PointLabelItem(GeoItem):

    def __init__(self, point: PointItem, text: str,
                 offset: QPointF = None):
        super().__init__()
        self._point = point
        self._text  = text
        self._moving_by_point = False   # guard: programmatic move
        self._font_family = "Times New Roman"
        self._font_size   = DEFAULT_FONT_SIZE
        # offset: vector từ scenePos(point) → scenePos(label-baseline-left)
        self._offset = QPointF(offset) if offset is not None \
            else self._offset_towards(_outward_dir(point))

        # Không dùng ItemIsMovable vì SelectTool dùng setPos() trực tiếp.
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,         True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable,            False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setZValue(15)

        point.add_dependent(self)
        self._sync_pos()

    # ── Text property ─────────────────────────────────────────────────────

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, value: str):
        self.prepareGeometryChange()
        self._text = value
        self._point.label = value    # keep point.label in sync
        self.update()

    # ── Font / cỡ chữ ────────────────────────────────────────────────────

    @property
    def font_family(self) -> str:
        return self._font_family

    @property
    def font_size(self) -> int:
        return self._font_size

    def style_state(self) -> tuple:
        """(text, family, size) — dùng cho undo/redo."""
        return (self._text, self._font_family, self._font_size)

    def apply_style_state(self, state: tuple):
        text, family, size = state
        self.prepareGeometryChange()
        self._font_family = family
        self._font_size   = max(6, min(96, int(size)))
        self.text = text

    def _max_dist(self) -> float:
        # Chữ to thì cho phép đặt nhãn xa điểm hơn
        return MAX_DIST * max(1.0, self._font_size / 13.0)

    def _offset_towards(self, d: tuple) -> QPointF:
        """Offset (baseline-trái) để tâm chữ nằm cách điểm LABEL_GAP theo hướng d."""
        fm = QFontMetricsF(self._font())
        w, asc = fm.horizontalAdvance(self._text or "A"), fm.ascent()
        # Lùi thêm theo kích thước chữ để chữ không đè lên điểm / đường
        gap = LABEL_GAP + abs(d[0]) * w / 2 + abs(d[1]) * asc * 0.35
        cx, cy = d[0] * gap, d[1] * gap
        return QPointF(cx - w / 2, cy + asc * 0.35)

    # ── Sync với điểm cha ────────────────────────────────────────────────

    def _sync_pos(self):
        """Đặt vị trí theo điểm + offset đã lưu (không kích hoạt clamp)."""
        self._moving_by_point = True
        self.setPos(self._point.scenePos() + self._offset)
        self._moving_by_point = False

    def update_position(self):
        """Gọi bởi PointItem.itemChange khi điểm di chuyển."""
        if self.isSelected():
            # SelectTool đang kéo nhãn trực tiếp — bỏ qua để tránh double-move
            return
        self._sync_pos()

    # ── Khi xóa khỏi scene ───────────────────────────────────────────────

    def remove_from_scene(self):
        self._point.remove_dependent(self)
        self._point.label = ""
        if getattr(self._point, '_label_item', None) is self:
            self._point._label_item = None

    # ── itemChange: clamp + khôi phục khi undo/redo ──────────────────────

    def itemChange(self, change, value):
        GIC = QGraphicsItem.GraphicsItemChange

        # ── Khi được thêm vào scene (kể cả undo/redo) ──────────────────
        if change == GIC.ItemSceneHasChanged:
            sc = self.scene()
            if sc is not None:
                # Khôi phục dependency nếu bị mất (ví dụ sau undo remove)
                if self not in self._point._dependents:
                    self._point.add_dependent(self)
                self._point.label = self._text
                self._point._label_item = self
            return value

        # ── Clamp khi người dùng kéo (không phải point kéo nhãn đi) ────
        if change == GIC.ItemPositionChange:
            if self._moving_by_point or self._point.isSelected():
                # Kéo đa-item hoặc programmatic → không constraint
                return value
            # Kéo nhãn một mình: giữ trong [MIN_DIST, MAX_DIST]
            pt  = self._point.scenePos()
            dx  = value.x() - pt.x()
            dy  = value.y() - pt.y()
            d   = math.sqrt(dx * dx + dy * dy)
            if d < 1e-9:
                return value
            max_d = self._max_dist()
            if d > max_d:
                s  = max_d / d
                dx *= s; dy *= s
            elif d < MIN_DIST:
                s  = MIN_DIST / d
                dx *= s; dy *= s
            return QPointF(pt.x() + dx, pt.y() + dy)

        # ── Sau khi kéo nhãn xong: cập nhật offset đã lưu ──────────────
        if change == GIC.ItemPositionHasChanged:
            if not self._moving_by_point and not self._point.isSelected():
                pt = self._point.scenePos()
                self._offset = QPointF(
                    self.scenePos().x() - pt.x(),
                    self.scenePos().y() - pt.y(),
                )
            return value

        return super().itemChange(change, value)

    # ── Vẽ ───────────────────────────────────────────────────────────────

    def _font(self) -> QFont:
        f = QFont(self._font_family, self._font_size)
        f.setItalic(True)
        return f

    def boundingRect(self) -> QRectF:
        if not self._text:
            return QRectF(-2, -2, 4, 4)
        fm  = QFontMetricsF(self._font())
        w   = fm.horizontalAdvance(self._text)
        asc = fm.ascent()
        des = fm.descent()
        pad = 3
        return QRectF(-pad, -(asc + pad), w + pad * 2, asc + des + pad * 2)

    def paint(self, painter: QPainter, option, widget=None):
        if not self._text:
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        selected = self.isSelected()
        if selected:
            painter.fillRect(
                self.boundingRect(),
                QColor(0, 120, 215, 28))
        color = QColor(0, 90, 200) if selected else QColor(20, 20, 20)
        painter.setFont(self._font())
        painter.setPen(QPen(color, 1.0))
        # drawText với baseline tại (0, 0)
        painter.drawText(QPointF(0, 0), self._text)


# ── Tự chọn hướng đặt nhãn ───────────────────────────────────────────────────

def _unit(dx: float, dy: float):
    L = math.hypot(dx, dy)
    return (dx / L, dy / L) if L > 1e-9 else None


def _figure_centroid(scene, skip):
    pts = [p.scenePos() for p in scene.point_items() if p is not skip] \
        if scene is not None else []
    if not pts:
        return None
    return (sum(p.x() for p in pts) / len(pts), sum(p.y() for p in pts) / len(pts))


def _busy_dirs(point) -> list:
    """Các hướng (vector đơn vị) từ điểm theo những đường / điểm nối với nó."""
    from items.on_curve import PointOnCurveItem, IntersectionPointItem
    from items.line import LineItem
    from utils.snap_engine import curves_of
    p = point.scenePos()
    dirs = []

    def towards(q, both=False):
        u = _unit(q.x() - p.x(), q.y() - p.y())
        if u:
            dirs.append(u)
            if both:
                dirs.append((-u[0], -u[1]))

    def along(curve):
        if curve[0] == 'circle':
            c = curve[1]
            u = _unit(p.x() - c.x(), p.y() - c.y())
            if u:                       # tiếp tuyến tại điểm + hướng vào tâm
                dirs.extend([(-u[1], u[0]), (u[1], -u[0]), (-u[0], -u[1])])
        else:
            a, b = curve[1], curve[2]
            u = _unit(b.x() - a.x(), b.y() - a.y())
            if u:
                dirs.extend([u, (-u[0], -u[1])])

    for dep in point._dependents:
        if hasattr(dep, 'p1') and hasattr(dep, 'p2'):
            other = dep.p2 if dep.p1 is point else dep.p1
            towards(other.scenePos(), both=isinstance(dep, LineItem))
        elif isinstance(dep, PointItem) and dep.isVisible():
            towards(dep.scenePos())
        elif hasattr(dep, 'center_pt') and dep.center_pt is point:
            continue                    # tâm đường tròn: không vướng gì
        else:
            for c in curves_of(dep):
                along(c)
    hosts = []
    if isinstance(point, PointOnCurveItem):
        hosts = [(point._host, point._index)]
    elif isinstance(point, IntersectionPointItem):
        hosts = list(point._hosts)
    for host, k in hosts:
        cs = curves_of(host)
        if k < len(cs):
            along(cs[k])
    for attr in ('_p1', '_p2', '_src', '_a'):    # trung điểm, ảnh biến hình…
        q = getattr(point, attr, None)
        if isinstance(q, PointItem):
            towards(q.scenePos())
    return dirs


def _outward_dir(point) -> tuple:
    """Hướng đặt nhãn: xa các đường đi qua điểm, ưu tiên phía ngoài hình."""
    p = point.scenePos()
    cen = _figure_centroid(point.scene(), point)
    away = _unit(p.x() - cen[0], p.y() - cen[1]) if cen else None
    away = away or (0.7071, -0.7071)           # mặc định: phía trên-phải
    dirs = _busy_dirs(point)
    best, best_score = away, -1e9
    for k in range(24):
        t = k * math.pi / 12
        d = (math.cos(t), math.sin(t))
        gap = min((math.acos(max(-1.0, min(1.0, d[0] * u[0] + d[1] * u[1])))
                   for u in dirs), default=math.pi)
        score = min(gap, math.pi / 2) + 0.6 * (d[0] * away[0] + d[1] * away[1])
        if score > best_score:
            best, best_score = d, score
    return best


# ── Tên cho đường thẳng / tia ────────────────────────────────────────────────
# Tên đường dùng lại PointLabelItem, gắn vào một điểm neo ẩn nằm trên đường
# (PointOnCurveItem) → nhãn đi theo khi đường di chuyển, kéo được quanh điểm neo.

NAMEABLE_LINE_HINT = "đường thẳng / tia"


def nameable_line_at(scene, pos: QPointF, max_dist: float = 8.0):
    """Đường thẳng / tia gần pos nhất (trong max_dist px), hoặc None."""
    from items.line import LineItem, RayItem
    from utils.snap_engine import curves_of
    from items.on_curve import _param_of, _pos_of
    best, best_d = None, max_dist
    for it in scene.items():
        if not isinstance(it, (LineItem, RayItem)) or not it.isVisible():
            continue
        for c in curves_of(it):
            foot = _pos_of(c, _param_of(c, pos))
            d = math.hypot(foot.x() - pos.x(), foot.y() - pos.y())
            if d < best_d:
                best, best_d = it, d
    return best


def line_name_label(scene, line):
    """PointLabelItem đang làm tên cho line, hoặc None."""
    for it in scene.items():
        if isinstance(it, PointLabelItem) and \
                getattr(it._point, 'host', None) is line:
            return it
    return None


def line_names_used(scene) -> set:
    from items.on_curve import PointOnCurveItem
    return {it.label for it in scene.items()
            if isinstance(it, PointOnCurveItem) and not it.isVisible()
            and it.label}


def next_line_name(scene) -> str:
    """d, d1, d2… — tên đường chưa dùng."""
    used = line_names_used(scene)
    n = 0
    while ("d" + (str(n) if n else "")) in used:
        n += 1
    return "d" + (str(n) if n else "")


def make_line_name(scene, line, pos: QPointF, name: str) -> list:
    """
    Tạo [điểm neo ẩn, nhãn] đặt tên cho line tại chỗ gần pos nhất trên đường.
    Chưa addItem — gọi history.push_add_batch(scene, items).
    """
    from utils.snap_engine import curves_of
    from items.on_curve import PointOnCurveItem, anchor_points, _param_of, _pos_of
    c = curves_of(line)[0]
    foot = _pos_of(c, _param_of(c, pos))
    anchor = PointOnCurveItem(line, 0, foot, anchor_points(scene, line))
    anchor.setVisible(False)
    anchor.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
    anchor.label = name
    # Nhãn đặt vuông góc với đường, về phía ngoài hình
    a, b = c[1], c[2]
    u = _unit(b.x() - a.x(), b.y() - a.y()) or (1.0, 0.0)
    n = (-u[1], u[0])
    cen = _figure_centroid(scene, None)
    ref = cen if cen else (pos.x(), pos.y())
    if (foot.x() - ref[0]) * n[0] + (foot.y() - ref[1]) * n[1] < 0:
        n = (-n[0], -n[1])
    label = PointLabelItem(anchor, name, QPointF(0, 0))
    label._offset = label._offset_towards(n)
    label._sync_pos()
    return [anchor, label]


def with_line_names(scene, items: list) -> list:
    """Xóa đường / tia → xóa luôn tên của nó (nhãn + điểm neo)."""
    result = list(items)
    for it in items:
        lbl = line_name_label(scene, it)
        if lbl is not None:
            for extra in (lbl, lbl._point):
                if extra not in result:
                    result.append(extra)
    return result
