"""Nhập số đo góc cho tam giác thường (đa giác 3 đỉnh) và tam giác cân."""
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
    for it in hits:
        shp = shape_of(it)
        if shp is not None and _is_isosceles(shp):
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
