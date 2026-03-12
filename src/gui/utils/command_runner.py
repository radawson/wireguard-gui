import shlex
import subprocess as sp
from dataclasses import dataclass
from typing import List

from gui.errors import CommandExecutionError


@dataclass
class CommandResult:
    command: List[str]
    stdout: str
    stderr: str
    returncode: int


def _build_command(command: str) -> List[str]:
    return shlex.split(command)


def run_command(command: str) -> CommandResult:
    cmd_list = _build_command(command)
    result = sp.run(cmd_list, stderr=sp.PIPE, stdout=sp.PIPE, text=True, check=False)
    if result.returncode != 0:
        raise CommandExecutionError(command, result.returncode, result.stderr)
    return CommandResult(
        command=cmd_list,
        stdout=result.stdout,
        stderr=result.stderr,
        returncode=result.returncode,
    )


def run_sudo_command(command: str, password: str) -> CommandResult:
    cmd_list = ["sudo", "-S"] + _build_command(command)
    result = sp.run(
        cmd_list,
        input=password,
        stderr=sp.PIPE,
        stdout=sp.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise CommandExecutionError(command, result.returncode, result.stderr)
    return CommandResult(
        command=cmd_list,
        stdout=result.stdout,
        stderr=result.stderr,
        returncode=result.returncode,
    )
