"""Nhập số đo góc cho tam giác thường (đa giác 3 đỉnh), tam giác cân, và góc
tại một đỉnh của đa giác / tam giác."""
import math
from PyQt6.QtCore import QPointF
from PyQt6.QtWidgets import (QDialog, QFormLayout, QDoubleSpinBox, QLabel,
                             QDialogButtonBox, QVBoxLayout)


def _is_isosceles(item) -> bool:
    return getattr(item, "kind", "") == "isosceles_triangle"


def triangle_at(scene, hits: list):
    """Tam giác (thường hoặc cân) trong danh sách item tại vị trí click."""
    from items.shape import shape_of
    from items.polygon import PolygonItem
    from items.shape import FREE_KINDS
    for it in hits:
        shp = shape_of(it)
        if shp is not None and (_is_isosceles(shp) or
                                (shp.kind in FREE_KINDS and len(shp.points) == 3)):
            return shp
        if isinstance(it, PolygonItem) and len(it.points) == 3:
            return it
    return None


def _angle(at: QPointF, p: QPointF, q: QPointF) -> float:
    u = (p.x() - at.x(), p.y() - at.y())
    v = (q.x() - at.x(), q.y() - at.y())
    nu, nv = math.hypot(*u), math.hypot(*v)
    if nu < 1e-9 or nv < 1e-9:
        return 0.0
    c = max(-1.0, min(1.0, (u[0] * v[0] + u[1] * v[1]) / (nu * nv)))
    return math.degrees(math.acos(c))


def _rotate(v: QPointF, deg: float) -> QPointF:
    t = math.radians(deg)
    return QPointF(v.x() * math.cos(t) - v.y() * math.sin(t),
                   v.x() * math.sin(t) + v.y() * math.cos(t))


def _names(points: list) -> list:
    out = []
    for k, p in enumerate(points):
        out.append(getattr(p, "label", "") or "ABC"[k])
    return out


class _AnglesDialog(QDialog):
    def __init__(self, parent, names, angles, isosceles: bool):
        super().__init__(parent)
        self._iso = isosceles
        self._names = names
        self.setWindowTitle("Số đo góc tam giác")
        form = QFormLayout()
        a, b, c = names
        self._s1 = QDoubleSpinBox()
        self._s1.setDecimals(1)
        self._s1.setSuffix("°")
        self._info = QLabel()
        if isosceles:
            self._s1.setRange(1.0, 178.0)
            self._s1.setValue(round(angles[0], 1))
            form.addRow(f"Góc ở đỉnh {a}:", self._s1)
            self._s2 = None
        else:
            self._s1.setRange(1.0, 178.0)
            self._s1.setValue(round(angles[0], 1))
            self._s2 = QDoubleSpinBox()
            self._s2.setDecimals(1)
            self._s2.setSuffix("°")
            self._s2.setRange(1.0, 178.0)
            self._s2.setValue(round(angles[1], 1))
            form.addRow(f"Góc {a}:", self._s1)
            form.addRow(f"Góc {b}:", self._s2)
            self._s2.valueChanged.connect(self._update_info)
        self._s1.valueChanged.connect(self._update_info)
        form.addRow("", self._info)
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(self._buttons)
        self._update_info()

    def _update_info(self, *_):
        a, b, c = self._names
        ok = True
        if self._iso:
            base = (180.0 - self._s1.value()) / 2
            self._info.setText(f"Góc {b} = góc {c} = {base:.1f}°")
        else:
            rest = 180.0 - self._s1.value() - self._s2.value()
            ok = rest > 0.05
            self._info.setText(f"Góc {c} = {rest:.1f}°" if ok
                               else "Tổng 2 góc phải nhỏ hơn 180°")
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(ok)

    def values(self) -> tuple:
        return (self._s1.value(), self._s2.value() if self._s2 else None)


def edit_triangle_angles(item, scene, history) -> bool:
    """Mở hộp nhập góc; giữ nguyên cạnh AB (đỉnh 1, 2), di chuyển đỉnh 3."""
    pts = item.points
    A, B, C = (p.scenePos() for p in pts)
    iso = _is_isosceles(item)
    angles = (_angle(A, B, C), _angle(B, A, C))
    views = scene.views()
    dlg = _AnglesDialog(views[0] if views else None, _names(pts), angles, iso)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return False
    alpha, beta = dlg.values()
    ab = B - A
    side = 1.0 if (ab.x() * (C - A).y() - ab.y() * (C - A).x()) >= 0 else -1.0
    if iso:
        new_c = A + _rotate(ab, side * alpha)          # |AC| = |AB|
    else:
        c_len = math.hypot(ab.x(), ab.y())
        ac_len = c_len * math.sin(math.radians(beta)) / \
            math.sin(math.radians(alpha + beta))
        u = _rotate(ab, side * alpha)
        L = math.hypot(u.x(), u.y()) or 1.0
        new_c = A + u * (ac_len / L)
    target = pts[2]
    if getattr(target, "is_constrained", False):
        return False
    history.push_move(target, QPointF(target.pos()), new_c)
    return True


# ── Góc tại một đỉnh của đa giác / tam giác ──────────────────────────────────

def polygon_at_vertex(pt):
    """(đa giác, chỉ số đỉnh) mà pt là đỉnh, hoặc None."""
    from items.shape import ShapeItem, FREE_KINDS
    for d in getattr(pt, "_dependents", ()):
        if isinstance(d, ShapeItem) and d.kind in FREE_KINDS \
                and d.scene() is not None and pt in d.points:
            return d, d.points.index(pt)
    return None


def _cross(a: QPointF, b: QPointF) -> float:
    return a.x() * b.y() - a.y() * b.x()


def _orientation(pts: list) -> float:
    """+1 / −1 theo chiều vẽ đa giác (dấu diện tích có hướng)."""
    n = len(pts)
    s = sum(_cross(pts[k], pts[(k + 1) % n]) for k in range(n))
    return 1.0 if s >= 0 else -1.0


def interior_angle(pts: list, k: int) -> float:
    """Góc trong của đa giác tại đỉnh k (0–360°, đa giác lõm có góc > 180°)."""
    n = len(pts)
    a = pts[k - 1] - pts[k]
    b = pts[(k + 1) % n] - pts[k]
    t = math.degrees(math.atan2(_cross(b, a), b.x() * a.x() + b.y() * a.y()))
    return (t * _orientation(pts)) % 360.0


def edit_vertex_angle(poly, k: int, scene, history) -> bool:
    """
    Đổi góc tại đỉnh k: chỉ đỉnh kế tiếp (theo thứ tự vẽ) quay quanh đỉnh k,
    giữ nguyên độ dài cạnh; các đỉnh vẽ trước đỉnh k đứng yên.
    """
    from PyQt6.QtWidgets import QInputDialog, QMessageBox
    pts_items = poly.points
    n = len(pts_items)
    nxt = pts_items[(k + 1) % n]
    views = scene.views()
    parent = views[0] if views else None
    names = [getattr(p, "label", "") or f"đỉnh {i + 1}"
             for i, p in enumerate(pts_items)]
    if getattr(nxt, "is_constrained", False):
        QMessageBox.information(parent, "Số đo góc",
                                f"Không đổi được: {names[(k + 1) % n]} là điểm "
                                "dựng hình, không di chuyển tự do được.")
        return False
    pts = [p.scenePos() for p in pts_items]
    cur = interior_angle(pts, k)
    hi = 179.9 if n == 3 else 359.9
    val, ok = QInputDialog.getDouble(
        parent, "Số đo góc",
        f"Góc tại {names[k]} (đổi bằng cách di chuyển {names[(k + 1) % n]}):",
        round(cur, 1), 0.1, hi, 1)
    if not ok:
        return False
    a = pts[k - 1] - pts[k]
    b = pts[(k + 1) % n] - pts[k]
    la, lb = math.hypot(a.x(), a.y()), math.hypot(b.x(), b.y())
    if la < 1e-9 or lb < 1e-9:
        return False
    u = _rotate(a, -_orientation(pts) * val)
    new_pos = pts[k] + u * (lb / la)
    history.push_move(nxt, QPointF(nxt.pos()), new_pos)
    return True
