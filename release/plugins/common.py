import subprocess
import sys
import traceback
from functools import partial
from typing import Callable, Optional

from termcolor import colored


symbol = "#"


class BashFunc:
    def __init__(self, func: Optional[str] = None, **kwargs):
        self.func = func
        self.kwargs = kwargs

    def __call__(self) -> str:
        if self.func is None:
            return ""

        print(f"> {self}")
        try:
            output = subprocess.check_output(
                str(self), shell=True, stderr=subprocess.STDOUT
            )
        except Exception as exc:
            output = getattr(exc, "output", b"").decode("utf-8")
            print_error(f"ERROR: {exc}, Output:\n{output}", with_traceback=True)
            exit(1)
        return output.decode("utf-8")

    def __str__(self):
        try:
            return self.func.format(**self.kwargs)
        except Exception as exc:
            print_error(
                f"Error: {exc}. In formatting bash function: `{self.func}` with parameters: `{self.kwargs}`"
            )
            exit(1)


class Hooks:
    get_version: Callable[..., BashFunc]
    set_version: Callable[..., BashFunc]

    def __init__(self, **kwargs):
        for hook, command in kwargs.items():
            setattr(self, hook, partial(BashFunc, command))


def print_error(msg, with_traceback=False):
    # Handle stderr manually (print colored text to stdout)
    # because TravisCI will try hard to confuse you: loose or misplace error log
    print(colored(msg, "red"))
    if with_traceback:
        traceback.print_exc(file=sys.stdout)


def print_title(msg):
    print(colored(f"\n{symbol} {msg}\n", "green"))


def print_section(msg):
    print(colored(f"\n{symbol}\n{symbol} {msg}\n{symbol}\n", "yellow"))
