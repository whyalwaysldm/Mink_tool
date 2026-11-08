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


# ── Góc tại một đỉnh của đa giác / tam giác / hình bình hành… ────────────────

# Hình có góc đổi được (hình vuông, chữ nhật, đa giác đều… có góc cố định)
_SIDE_KINDS = ("parallelogram", "rhombus")
ANGLE_KINDS = ("polygon", "triangle", "trapezoid") + _SIDE_KINDS


def polygon_at_vertex(pt):
    """(hình, chỉ số đỉnh) mà pt là đỉnh và góc tại đó đổi được, hoặc None."""
    from items.shape import ShapeItem
    for d in getattr(pt, "_dependents", ()):
        if isinstance(d, ShapeItem) and d.kind in ANGLE_KINDS \
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


def _turn(center: QPointF, ref: QPointF, length_of: QPointF,
          deg: float) -> QPointF:
    """Điểm cách center bằng |length_of − center|, theo hướng (ref − center)
    quay deg độ."""
    v = ref - center
    lv = math.hypot(v.x(), v.y())
    w = length_of - center
    lw = math.hypot(w.x(), w.y())
    if lv < 1e-9 or lw < 1e-9:
        return None
    return center + _rotate(v, deg) * (lw / lv)


def angle_targets(kind: str, pts: list, k: int, val: float):
    """
    Vị trí mới các đỉnh để góc tại đỉnh k bằng val (None → không làm được).
      • đa giác / tam giác: đỉnh kế tiếp (theo thứ tự vẽ) quay quanh đỉnh k,
        các đỉnh khác đứng yên;
      • hình bình hành / thoi: đỉnh k và đỉnh trước nó đứng yên, đỉnh kế tiếp
        quay quanh k (giữ độ dài cạnh), đỉnh thứ tư tự đặt;
      • hình thang: đáy 0–1 đứng yên, cạnh bên phía đỉnh k quay quanh đầu mút
        trên đáy, đáy nhỏ tịnh tiến theo (giữ độ dài).
    """
    n = len(pts)
    o = _orientation(pts)
    out = list(pts)
    if kind in _SIDE_KINDS:
        nxt = _turn(pts[k], pts[k - 1], pts[(k + 1) % n], -o * val)
        if nxt is None:
            return None
        out[(k + 1) % n] = nxt
        out[(k + 2) % n] = pts[k - 1] + (nxt - pts[k])
    elif kind == "trapezoid":
        # góc ở 2 đỉnh kề một cạnh bên bù nhau
        beta = val if k in (0, 1) else 180.0 - val
        if k in (0, 3):
            top = _turn(pts[0], pts[1], pts[3], o * beta)
            if top is None:
                return None
            d = top - pts[3]
        else:
            top = _turn(pts[1], pts[0], pts[2], -o * beta)
            if top is None:
                return None
            d = top - pts[2]
        out[2] = pts[2] + d
        out[3] = pts[3] + d
        # cạnh bên không được cắt nhau (hình phải lồi)
        if _orientation(out) != o or \
                any(interior_angle(out, i) >= 180.0 for i in range(n)):
            return None
    else:
        nxt = _turn(pts[k], pts[k - 1], pts[(k + 1) % n], -o * val)
        if nxt is None:
            return None
        out[(k + 1) % n] = nxt
    return out


def edit_vertex_angle(poly, k: int, scene, history) -> bool:
    """Hỏi số đo góc tại đỉnh k rồi đổi hình theo angle_targets."""
    from PyQt6.QtWidgets import QInputDialog, QMessageBox
    items = poly.points
    n = len(items)
    views = scene.views()
    parent = views[0] if views else None
    names = [getattr(p, "label", "") or f"đỉnh {i + 1}"
             for i, p in enumerate(items)]
    pts = [p.scenePos() for p in items]
    cur = interior_angle(pts, k)
    hi = 359.9 if (poly.kind == "polygon" and n > 3) else 179.9
    if poly.kind in ("polygon", "triangle"):
        how = f" (đổi bằng cách di chuyển {names[(k + 1) % n]})"
    else:
        how = ""
    val, ok = QInputDialog.getDouble(
        parent, "Số đo góc", f"Góc tại {names[k]}{how}:",
        round(cur, 1), 0.1, hi, 1)
    if not ok:
        return False
    out = angle_targets(poly.kind, pts, k, val)
    if out is None:
        QMessageBox.information(parent, "Số đo góc",
                                f"Không đặt được góc {val:g}° cho "
                                f"{poly.shape_label} này.")
        return False
    moves = [(it, QPointF(it.pos()), it.pos() + (out[i] - pts[i]))
             for i, it in enumerate(items)
             if (out[i] - pts[i]).manhattanLength() > 1e-9]
    stuck = [names[items.index(m[0])] for m in moves
             if getattr(m[0], "is_constrained", False)]
    if stuck:
        QMessageBox.information(parent, "Số đo góc",
                                f"Không đổi được: {', '.join(stuck)} là điểm "
                                "dựng hình, không di chuyển tự do được.")
        return False
    history.push_move_group(moves)
    return True
