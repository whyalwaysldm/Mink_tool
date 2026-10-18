from PyQt6.QtGui import QUndoStack, QUndoCommand
from PyQt6.QtWidgets import QGraphicsScene


class _AddCmd(QUndoCommand):
    def __init__(self, scene: QGraphicsScene, item):
        super().__init__("Add item")
        self.scene = scene
        self.item = item

    def redo(self):
        self.scene.addItem(self.item)

    def undo(self):
        self.scene.removeItem(self.item)
        if hasattr(self.item, 'remove_from_scene'):
            self.item.remove_from_scene()


class _RemoveCmd(QUndoCommand):
    def __init__(self, scene: QGraphicsScene, items: list):
        super().__init__("Remove items")
        self.scene = scene
        self.items = list(items)

    def redo(self):
        for item in self.items:
            self.scene.removeItem(item)
            if hasattr(item, 'remove_from_scene'):
                item.remove_from_scene()

    def undo(self):
        for item in self.items:
            self.scene.addItem(item)


class _VisibilityCmd(QUndoCommand):
    """Ẩn / hiện một nhóm item — undo khôi phục trạng thái cũ từng item."""

    def __init__(self, items: list, hidden: bool):
        super().__init__("Ẩn" if hidden else "Hiện")
        self.items      = list(items)
        self.new_hidden = hidden
        # Ghi lại trạng thái trước khi thực hiện
        self.old_states = [getattr(it, '_is_hidden', False) for it in items]

    def redo(self):
        for it in self.items:
            if hasattr(it, 'set_hidden'):
                it.set_hidden(self.new_hidden)

    def undo(self):
        for it, old in zip(self.items, self.old_states):
            if hasattr(it, 'set_hidden'):
                it.set_hidden(old)


class _MoveCmd(QUndoCommand):
    def __init__(self, item, old_pos, new_pos):
        super().__init__("Move")
        self.item = item
        self.old_pos = old_pos
        self.new_pos = new_pos

    def redo(self):
        self.item.setPos(self.new_pos)

    def undo(self):
        self.item.setPos(self.old_pos)


class _LabelStyleCmd(QUndoCommand):
    """Đổi nội dung / font / cỡ chữ của nhãn."""
    def __init__(self, item, old_state, new_state):
        super().__init__("Label style")
        self.item = item
        self.old_state = old_state
        self.new_state = new_state

    def redo(self):
        self.item.apply_style_state(self.new_state)

    def undo(self):
        self.item.apply_style_state(self.old_state)


class _MoveGroupCmd(QUndoCommand):
    """Di chuyển nhiều item cùng lúc (tắt ràng buộc hình mẫu khi undo/redo)."""
    def __init__(self, moves: list):
        super().__init__("Move items")
        self.moves = list(moves)      # [(item, old_pos, new_pos)]

    def _apply(self, idx):
        from items.shape import constraints_suspended
        with constraints_suspended():
            for m in self.moves:
                m[0].setPos(m[idx])

    def redo(self):
        self._apply(2)

    def undo(self):
        self._apply(1)


class History:
    def __init__(self):
        self._stack = QUndoStack()

    @property
    def stack(self) -> QUndoStack:
        return self._stack

    def push_add(self, scene, item):
        self._stack.push(_AddCmd(scene, item))

    def push_add_batch(self, scene, items: list):
        self._stack.beginMacro("Add items")
        for item in items:
            self._stack.push(_AddCmd(scene, item))
        self._stack.endMacro()

    def push_remove(self, scene, items):
        if not isinstance(items, list):
            items = [items]
        self._stack.push(_RemoveCmd(scene, items))

    def push_visibility(self, items, hidden: bool):
        """Ẩn hoặc hiện danh sách items, với undo/redo."""
        if not isinstance(items, list):
            items = [items]
        self._stack.push(_VisibilityCmd(items, hidden))

    def push_move(self, item, old_pos, new_pos):
        self._stack.push(_MoveCmd(item, old_pos, new_pos))

    def push_move_group(self, moves: list):
        """moves = [(item, old_pos, new_pos)] — 1 bước undo cho cả nhóm."""
        moves = [m for m in moves if m[1] != m[2]]
        if len(moves) == 1:
            self.push_move(*moves[0])
        elif moves:
            self._stack.push(_MoveGroupCmd(moves))

    def push_label_style(self, item, old_state, new_state):
        if old_state != new_state:
            self._stack.push(_LabelStyleCmd(item, old_state, new_state))

    def can_undo(self) -> bool:
        return self._stack.canUndo()

    def can_redo(self) -> bool:
        return self._stack.canRedo()

    def undo(self):
        self._stack.undo()

    def redo(self):
        self._stack.redo()
