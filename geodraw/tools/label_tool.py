from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtWidgets import QInputDialog
from .base_tool import BaseTool
from items.label import LabelItem


class LabelTool(BaseTool):
    name = "label"

    def press(self, pos: QPointF, button, modifiers):
        if button != Qt.MouseButton.LeftButton:
            return
        view = self.scene.views()[0] if self.scene.views() else None
        text, ok = QInputDialog.getText(view, "Nhập nhãn", "Nội dung:")
        if ok and text.strip():
            lbl = LabelItem(text.strip(), pos)
            self.scene.addItem(lbl)
            self.history.push_add(self.scene, lbl)
