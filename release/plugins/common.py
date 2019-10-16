import subprocess
import sys
from functools import partial
from typing import Callable, Optional


symbol = "#"


class BashFunc:
    def __init__(self, func: Optional[str] = None, **kwargs):
        self.func = func
        self.kwargs = kwargs

    def __call__(self) -> str:
        if self.func is None:
            return ""

        print(f"> {self}")
        output = subprocess.check_output(str(self), shell=True)
        return output.decode("utf-8")

    def __str__(self):
        return self.func.format(**self.kwargs)


class Hooks:
    get_version: Callable[..., BashFunc]
    set_version: Callable[..., BashFunc]

    def __init__(self, **kwargs):
        for hook, command in kwargs.items():
            setattr(self, hook, partial(BashFunc, command))


def print_error(msg):
    sys.stderr.write(f"{msg}\n")


def print_title(msg):
    print(f"\n{symbol} {msg}\n")


def print_section(msg):
    print(f"\n{symbol}\n{symbol} {msg}\n{symbol}\n")
