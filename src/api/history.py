from typing import List

from api.data_structures import SimpleStack
from api.operation import Operation


class HistoryManager:

    def __init__(self):
        self.undo_stack: List[Operation] = []
        self.redo_stack: SimpleStack[Operation] = SimpleStack()

    def run_operation(self, operation_instance: Operation):
        self.undo_stack.append(operation_instance)

    def undo(self):
        self.redo_stack.append(self.undo_stack.pop())

    def redo(self):
        self.undo_stack.append(self.redo_stack.pop())
