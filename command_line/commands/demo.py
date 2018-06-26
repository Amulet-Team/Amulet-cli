from typing import List

from api.cmd_line import SimpleCommand, Mode


class TestCommand(SimpleCommand):

    def short_help(self) -> str:
        return "Test Command"

    def run(self, args: List[str]):
        print("This is a test command that doesn't do anything!")

    def help(self):
        print("This command does nothing notable")

    command = "test"


class EchoCommand(SimpleCommand):

    def short_help(self) -> str:
        return "Echoes the entire command and arguments"

    def run(self, args: List[str]):
        print(f'Got the following command: {" ".join(args)}')

    def help(self):
        print("Echoes the supplied command and it's arguments back to the user")

    command = "echo"

class EnterTestModeCommand(SimpleCommand):

    command = "entertestmode"

    def run(self, args: List[str]):
        mode = TestMode(self.handler, '-b' in args)
        self.handler.enter_mode(mode)

    def help(self):
        pass

    def short_help(self) -> str:
        return "Enters a new mode"


class TestMode(Mode):

    def __init__(self, handler, should_halt_exit=False):
        super(TestMode, self).__init__(handler)
        self._block_exit = not should_halt_exit

    def before_execution(self, command) -> bool:
        return True

    def display(self):
        return "Test Mode"

    def enter(self):
        print("Entering test mode")

    def exit(self):
        print("Exiting test mode")
        return self._block_exit
