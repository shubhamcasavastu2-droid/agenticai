"""Shell-command safety checks for the bash tool.

This is a best-effort guard, not a sandbox: it tokenizes the command with shlex, splits it on
shell operators, unwraps common wrappers (env, nohup, `bash -c "..."`) and applies rules to each
simple command. Commands it does not deny still go through the interactive permission prompt.
"""

from __future__ import annotations

import os
import re
import shlex
from pathlib import Path

SEPARATORS = {";", "&&", "||", "|", "&", "\n", "|&", ";;"}
SHELLS = {"sh", "bash", "zsh", "dash", "ksh", "fish"}
INTERPRETERS = SHELLS | {"python", "python3", "perl", "ruby", "node"}
DOWNLOADERS = {"curl", "wget"}
PRIVILEGE = {"sudo", "doas", "su", "pkexec"}
PASSTHROUGH_WRAPPERS = {"env", "nohup", "time", "nice", "command", "builtin", "exec", "timeout", "xargs"}
POWER = {"shutdown", "reboot", "halt", "poweroff"}
DISK_TOOLS = {"fdisk", "sfdisk", "parted", "wipefs"}
CRITICAL_PATHS = {
    "/", "/bin", "/boot", "/dev", "/etc", "/home", "/lib", "/opt", "/private", "/root", "/sbin",
    "/System", "/Library", "/Applications", "/Users", "/usr", "/var",
}
FORK_BOMB = re.compile(r":\s*\(\s*\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:")
RAW_DEVICE_WRITE = re.compile(r">\s*/dev/(sd|hd|nvme|disk|rdisk)")


def _tokenize(command: str) -> list[str] | None:
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|")
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        return list(lexer)
    except ValueError:
        return None


def _segments(tokens: list[str]) -> list[tuple[list[str], str | None]]:
    """Split tokens into simple commands. Each entry is (argv, operator that follows it)."""
    segments: list[tuple[list[str], str | None]] = []
    current: list[str] = []
    for token in tokens:
        if token in SEPARATORS:
            segments.append((current, token))
            current = []
        else:
            current.append(token)
    segments.append((current, None))
    return [(argv, op) for argv, op in segments if argv]


def _strip_wrappers(argv: list[str]) -> list[str]:
    """Drop leading VAR=value assignments and pass-through wrappers such as `env` or `nohup`."""
    index = 0
    while index < len(argv):
        word = argv[index]
        name = os.path.basename(word)
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", word):
            index += 1
        elif name in PASSTHROUGH_WRAPPERS:
            index += 1
            # skip wrapper options like `env -i`, `nice -n 5`, `timeout 10`
            while index < len(argv) and (argv[index].startswith("-") or argv[index].isdigit()):
                index += 1
        else:
            break
    return argv[index:]


def _short_flags(argv: list[str]) -> set[str]:
    flags: set[str] = set()
    for word in argv[1:]:
        if word == "--":
            break
        if word.startswith("--"):
            flags.add(word)
        elif word.startswith("-") and len(word) > 1:
            flags.update(f"-{char}" for char in word[1:])
    return flags


def _is_critical_target(target: str, project_root: Path | None) -> bool:
    """True if a recursive rm/chmod/chown on `target` could reach beyond what we consider safe."""
    if target.startswith("$"):
        return True  # unexpanded variable: cannot prove it is safe
    expanded = os.path.expanduser(target)
    if project_root is not None:
        path = Path(expanded)
        if not path.is_absolute():
            path = project_root / path
        return not _within(Path(os.path.realpath(path)), project_root)
    normalized = os.path.normpath(expanded.rstrip("*") or "/")
    return normalized in CRITICAL_PATHS or normalized == os.path.expanduser("~")


def _within(path: Path, root: Path) -> bool:
    root = Path(os.path.realpath(root))
    try:
        return os.path.commonpath([str(root), str(path)]) == str(root)
    except ValueError:
        return False


def _check_simple_command(argv: list[str], project_root: Path | None, depth: int) -> str | None:
    argv = _strip_wrappers(argv)
    if not argv:
        return None
    name = os.path.basename(argv[0])

    if name in PRIVILEGE:
        return f"privilege escalation via '{name}' is not allowed"
    if name in POWER:
        return f"'{name}' would power off or restart the machine"
    if name.startswith("mkfs") or name in DISK_TOOLS:
        return f"'{name}' modifies disks or partitions"
    if name == "diskutil" and any(arg.lower().startswith(("erase", "partition", "zero")) for arg in argv[1:]):
        return "diskutil erase/partition is not allowed"
    if name == "dd" and any(arg.startswith("of=/dev/") for arg in argv[1:]):
        return "dd writing to a device is not allowed"

    if name == "rm":
        flags = _short_flags(argv)
        recursive = bool(flags & {"-r", "-R", "--recursive"})
        if recursive:
            targets = [arg for arg in argv[1:] if not arg.startswith("-")]
            for target in targets:
                if _is_critical_target(target, project_root):
                    where = "outside the project root" if project_root else "a critical path"
                    return f"recursive rm of '{target}' targets {where}"
        if "--no-preserve-root" in flags:
            return "rm --no-preserve-root is not allowed"

    if name in {"chmod", "chown", "chgrp"}:
        flags = _short_flags(argv)
        if flags & {"-R", "--recursive"}:
            targets = [arg for arg in argv[1:] if not arg.startswith("-")][1:]
            if any(_is_critical_target(target, project_root) for target in targets):
                return f"recursive {name} outside the project root is not allowed"

    if name == "git" and len(argv) > 1 and "push" in argv[1:3]:
        rest = argv[argv.index("push") + 1 :]
        if any(arg in {"--force", "-f"} or (arg.startswith("-") and not arg.startswith("--") and "f" in arg)
               for arg in rest):
            return "git push --force is not allowed (use --force-with-lease after confirming with the user)"
        if any(arg.startswith("+") for arg in rest):
            return "force-pushing a +refspec is not allowed"

    # bash -c "...", eval "...": check the nested command too
    if depth < 3:
        nested: str | None = None
        if name in SHELLS and "-c" in argv[1:]:
            position = argv.index("-c")
            nested = argv[position + 1] if position + 1 < len(argv) else None
        elif name == "eval":
            nested = " ".join(argv[1:])
        if nested:
            return find_denied_reason(nested, project_root, depth + 1)
    return None


def find_denied_reason(command: str, project_root: Path | None = None, depth: int = 0) -> str | None:
    """Return why `command` must be refused, or None if no rule matched."""
    if FORK_BOMB.search(command):
        return "fork bomb detected"
    if RAW_DEVICE_WRITE.search(command):
        return "redirecting output to a raw disk device is not allowed"

    tokens = _tokenize(command)
    if tokens is None:
        return "command could not be parsed (unbalanced quotes)"

    segments = _segments(tokens)
    for index, (argv, operator) in enumerate(segments):
        reason = _check_simple_command(argv, project_root, depth)
        if reason:
            return reason
        # curl ... | sh  /  wget -O- ... | python
        if operator in {"|", "|&"} and index + 1 < len(segments):
            source = _strip_wrappers(argv)
            sink = _strip_wrappers(segments[index + 1][0])
            if (
                source
                and sink
                and os.path.basename(source[0]) in DOWNLOADERS
                and os.path.basename(sink[0]) in INTERPRETERS | PRIVILEGE
            ):
                return "piping downloaded content into an interpreter is not allowed"

    # $(curl ...) or `curl ...` fed to a shell
    if re.search(r"(bash|sh|zsh)\s+(-c\s+)?[\"']?\$\((curl|wget)", command):
        return "executing downloaded content is not allowed"
    return None
