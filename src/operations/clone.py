from api.box import SubBox, SelectionBox
from api.operation import Operation, BlockChange

from typing import List


class Clone2(Operation):
    def __init__(self, source_box: SubBox, target_box: SubBox):
        self.source_box = source_box
        self.target_box = target_box

    def run_operation(self, world):
        if self.source_box.shape != self.target_box.shape:
            raise Exception("The shape of the selections needs to be the same")
        source_generator = world.get_blocks(*self.source_box.to_slice())
        target_generator = world.get_blocks(*self.target_box.to_slice())
        for target_selection in target_generator:
            source_selection = next(source_generator)
            target_selection.blocks = source_selection.blocks

class Clone(Operation):

    def __init__(self, source_box: SelectionBox, target_box: SelectionBox):
        self.source_box = source_box
        self.target_box = target_box
        self.changes: List[BlockChange] = []

    def __contains__(self, item):
        for block_change in self.changes:
            if item in block_change:
                return True
        return False

    def run_operation(self, world):
        if len(self.source_box) != len(self.target_box):
            raise Exception("Source Box and Target Box must have the same amount of subboexes")

        for source, target in zip(self.source_box.subboxes(), self.target_box.subboxes()):
            if source.shape != target.shape:
                raise Exception("The shape of the selections needs to be the same")
            source_generator = world.get_blocks(*source.to_slice())
            target_generator = world.get_blocks(*target.to_slice())
            for target_selection in target_generator:
                source_selection = next(source_generator)
                target_selection.blocks = source_selection.blocks

                self.changes.append(BlockChange(target.min, target_selection.blocks))

