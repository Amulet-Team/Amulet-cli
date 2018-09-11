import functools
import importlib
import shlex
import sys
import os
import re
import traceback
import time
from collections import namedtuple
import glob
from typing import Type

from prompt_toolkit import PromptSession, HTML, print_formatted_text
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.shortcuts import ProgressBar

from command_line import SimpleCommand, ComplexCommand, Mode
from command_line import builtin_commands
from command_line.builtin_commands import PopModeCommand

from api.data_structures import SimpleStack
from api.paths import COMMANDS_DIR

Command_Entry = namedtuple("Command", ("run", "short_help", "help"))


class ModeStack(SimpleStack):

    def __init__(self, *args, **kwargs):
        super(ModeStack, self).__init__(*args, **kwargs)

    def iter(self):
        for mode in self._data:
            yield mode.display()

    def has_mode(self, mode_class: Type[Mode]):
        return self.get_mode(mode_class) is not None

    def get_mode(self, mode_class: Type[Mode]):
        if not isinstance(mode_class, type):
            raise TypeError("You must pass a Type")

        for mode in self._data:
            if isinstance(mode, mode_class):
                return mode

        return None


class _CommandCompleter(Completer):

    def __init__(self, *args, **kwargs):
        super(_CommandCompleter, self).__init__(*args, **kwargs)
        self._completion_map = {"exit": None}

    def add_command(self, command_name, completion_callable):
        self._completion_map[command_name] = completion_callable

    def get_completions(self, document, complete_event):
        for cmd in self._completion_map.keys():
            text = document.text
            parts = shlex.split(text)
            if text.endswith(" "):
                parts.append(" ")
            if not parts:
                yield Completion(cmd, start_position=-len(text))

            elif cmd.startswith(parts[0]):
                if len(parts) == 1 and not text.endswith(" "):
                    yield Completion(cmd, start_position=-len(text))

                elif callable(self._completion_map[cmd]):
                    yield self._completion_map[cmd](parts[1:])


def _print(message: str, html=False):
    if html:
        message = HTML(message)
    print_formatted_text(message)


class PromptLineHandler:

    _reserved_commands = ("help", "exit")
    _command_regex = re.compile(r"^[a-zA-Z_]+\d*$")

    def __init__(self):
        self.shared_data = {}

        self._commands = {}
        self._complex_commands = {}
        self._completion_maps = {}

        self._modules = []

        self._modes = ModeStack()

        self._load_external = None

        self.in_mode = self._modes.has_mode
        self.get_mode = self._modes.get_mode

        self._completer = _CommandCompleter()
        self._session = PromptSession(completer=self._completer)

        self._load_commands()

    def _load_commands(self, reload=False):

        search_path = os.path.join(os.path.dirname(COMMANDS_DIR), "commands")
        sys.path.insert(0, os.path.join(search_path))

        commands = glob.glob(os.path.join(search_path, "*.py"))
        if commands:
            if self._load_external is None:
                _print(
                    "Detected loadable 3rd party command-line modules. These modules"
                )
                _print(
                    "cannot be verified to be stable and/or contain malicious code. If"
                )
                _print("you enable these modules, you use them at your own risk")
                answer = self._session.prompt(
                    "Would you like to enable them anyway? (y/n)> "
                )
                self._load_external = answer == "y"
            else:
                answer = "y" if self._load_external else "n"

            if answer.lower() == "y":
                failed_modules = []
                with ProgressBar(title="Loading 3rd-party modules") as pb:
                    for cmd in pb(commands):
                        time.sleep(0.25)
                        try:
                            module = importlib.import_module(os.path.basename(cmd)[:-3])
                            self._modules.append(module)
                        except Exception as e:
                            failed_modules.append(os.path.basename(cmd))

                for failed in failed_modules:
                    _print(f'<red>Failed to import "{failed}"</red>', html=True)

        simple_commands = SimpleCommand.get_subclasses()
        for cmd in simple_commands:

            if not getattr(cmd, "registered", False):
                continue

            command_func, command_name = cmd.command

            if not self._command_regex.match(command_name) and command_name != "$":
                _print(
                    f"<red>Could not enable command {command_name} since it doesn't have a valid command name/prefix</red>",
                    html=True,
                )
                continue

            if command_name in self._reserved_commands:
                _print(
                    f"<red>Could not enable command {command_name} since another command uses the same prefix!</red>",
                    html=True,
                )

            command_instance = cmd(self)
            self._commands[command_name] = Command_Entry(
                functools.partial(command_func, command_instance),
                command_instance.short_help,
                command_instance.help,
            )

            self._completer.add_command(
                command_name, getattr(command_instance, "completer", None)
            )

        complex_commands = ComplexCommand.get_subclasses()
        for cmd in complex_commands:

            if not getattr(cmd, "registered", False):
                continue

            base_command = cmd.base_command
            command_instance = cmd(self)

            self._complex_commands[base_command] = command_instance

            for command_name, func in cmd.sub_commands.items():
                self._commands[f"{base_command}.{command_name}"] = Command_Entry(
                    functools.partial(func, command_instance),
                    command_instance.short_help,
                    functools.partial(command_instance.help, command_name),
                )

    def enter_mode(self, mode: Mode):
        """
        Enters the supplied Mode, but doesn't add it to the ModeStack unless enter() returns True

        :param mode: An instance of Mode to enter
        """
        if mode.enter():
            self._modes.append(mode)
        else:
            _print(
                f"<yellow>=== Error: Could not enter mode: {mode.__class__.__name__}</yellow>",
                html=True,
            )

    def exit_mode(self, force: bool = False) -> bool:
        """
        Exits the most current Mode if the Mode's exit() returns True. If False is returned, the user is
        notified. If ``force`` is True, then the return value of exit() is ignored.

        :param force: True if the return value of exit() is to be ignored
        :return: True if the Mode was successfully exited, False otherwise
        """
        if self._modes.is_empty():
            return False

        mode = self._modes.peek()
        result = mode.exit()
        if force:
            self._modes.pop()
        elif not result:
            _print(
                f"<yellow>======= Could not exit {mode.display()} ======</yellow>",
                html=True,
            )
            return False

        else:
            self._modes.pop()
        return True

    def _execute_command(self, command_parts):
        try:
            self._commands[command_parts[0]].run(command_parts)
        except Exception as e:
            cmd = " ".join(command_parts)
            _print("<red>==== Begin Exception Stacktrace ====</red>", html=True)
            time.sleep(0.01)
            traceback.print_exc()
            time.sleep(0.01)
            _print("<red>==== End Exception Stacktrace ====</red>", html=True)
            _print(
                f"<red>=== Error: An Exception has occurred while running command: '{cmd}'</red>",
                html=True,
            )

    def _exit(self, force=False) -> bool:
        while not self._modes.is_empty():
            result = self.exit_mode(force)
            if not result:
                _print(f"<red>======= Could not exit {mode.display()} ======</red>")
                return False

        return True

    def run(self):
        while True:
            user_input = self._session.prompt(f"{' |'.join(self._modes.iter())}> ")

            if not user_input:
                continue

            if user_input.count('"') % 2 != 0 or user_input.count("'") % 2 != 0:
                _print(
                    "<red>=== Error: You do not have an even amount of quotations in your entered command, please re-enter your command</red>",
                    html=True,
                )
                continue

            command_parts = shlex.split(user_input)

            if command_parts[0] == "exit":
                if not self._exit("-f" in command_parts):
                    continue

                break

            if command_parts[0] == PopModeCommand.command:
                self._commands[command_parts[0]].run(command_parts)

            if command_parts[0].startswith("$"):
                self._commands["$"].run(command_parts)
                continue


def init():
    return PromptLineHandler()
