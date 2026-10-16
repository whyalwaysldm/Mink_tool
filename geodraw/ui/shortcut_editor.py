from PyQt6.QtWidgets import (QDialog, QTableWidget, QTableWidgetItem,
                              QVBoxLayout, QHBoxLayout, QPushButton,
                              QLabel, QHeaderView)
from PyQt6.QtCore import Qt


class ShortcutEditorDialog(QDialog):

    def __init__(self, tool_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cấu hình phím tắt")
        self.resize(420, 500)
        self._tm = tool_manager

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Nhấp đôi vào ô Phím để thay đổi. "
                                "Thay đổi có hiệu lực ngay."))

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["Phím", "Hành động"])
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked)
        layout.addWidget(self._table)

        btns = QHBoxLayout()
        ok = QPushButton("Đóng")
        ok.clicked.connect(self.accept)
        btns.addStretch()
        btns.addWidget(ok)
        layout.addLayout(btns)

        self._populate()
        self._table.cellChanged.connect(self._on_cell_changed)

    def _populate(self):
        self._table.setRowCount(0)
        self._table.blockSignals(True)
        for key, action in sorted(self._tm.shortcuts().items()):
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(key))
            item_action = QTableWidgetItem(action)
            item_action.setFlags(item_action.flags() &
                                 ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 1, item_action)
        self._table.blockSignals(False)

    def _on_cell_changed(self, row: int, col: int):
        if col != 0:
            return
        new_key = self._table.item(row, 0).text().strip()
        action = self._table.item(row, 1).text()
        if new_key:
            self._tm.update_shortcut(new_key, action)
