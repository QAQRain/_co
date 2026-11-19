#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM Parser：讀取 .vm、去掉註解、拆解成結構化的指令。

命名為 vm_parser 而不是 parser，是為了避開舊版 Python 的 parser 模組名稱。
每條指令都保留行號與原始碼片段，方便翻譯階段回報錯誤。
"""

from __future__ import annotations

import string
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from vm_error import VmError

ARITHMETIC_COMMANDS = {
    "add", "sub", "neg", "not", "eq", "gt", "lt", "and", "or",
}
SEGMENTS = {
    "constant", "local", "argument", "this", "that",
    "temp", "pointer", "static",
}
SYMBOL_FIRST = set(string.ascii_letters + "_.$:")
SYMBOL_REST = SYMBOL_FIRST | set(string.digits)
MAX_INDEX = 32767


class CommandType(Enum):
    """VM 指令的九種類型。"""

    C_ARITHMETIC = "C_ARITHMETIC"
    C_PUSH = "C_PUSH"
    C_POP = "C_POP"
    C_LABEL = "C_LABEL"
    C_GOTO = "C_GOTO"
    C_IF = "C_IF"
    C_FUNCTION = "C_FUNCTION"
    C_CALL = "C_CALL"
    C_RETURN = "C_RETURN"


@dataclass(frozen=True)
class Command:
    """一條已解析的 VM 指令。"""

    type: CommandType
    arg1: str | None
    arg2: int | None
    lineno: int
    source: str


def read_source_lines(path: Path) -> list[str]:
    """先試 UTF-8（順便吃掉 BOM），再退回 cp950。"""
    if not path.is_file():
        raise FileNotFoundError(f"找不到檔案：{path}")
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = path.read_text(encoding="cp950", errors="replace")
    return text.splitlines()


class Parser:
    """把一個 .vm 檔解析成 Command 串列。"""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        lines = read_source_lines(self.path)
        self._commands: list[Command] = []
        for lineno, raw in enumerate(lines, start=1):
            command = self._parse_line(lineno, raw)
            if command is not None:
                self._commands.append(command)

    def __iter__(self):
        return iter(self._commands)

    def __len__(self) -> int:
        return len(self._commands)

    def _fail(self, lineno: int, source: str, message: str) -> VmError:
        return VmError(lineno, source, message, self.path)

    def _parse_index(self, text: str, lineno: int, source: str) -> int:
        if not (text.isascii() and text.isdigit()):
            raise self._fail(lineno, source, f"索引「{text}」必須是非負整數")
        value = int(text)
        if value > MAX_INDEX:
            raise self._fail(lineno, source, f"索引 {value} 超出範圍（0~{MAX_INDEX}）")
        return value

    def _check_symbol(self, name: str, lineno: int, source: str) -> None:
        if not name:
            raise self._fail(lineno, source, "名稱不可為空")
        if name[0] not in SYMBOL_FIRST:
            raise self._fail(lineno, source, f"名稱「{name}」不能以「{name[0]}」開頭")
        for ch in name[1:]:
            if ch not in SYMBOL_REST:
                raise self._fail(lineno, source, f"名稱「{name}」含有非法字元「{ch}」")

    def _parse_line(self, lineno: int, raw: str) -> Command | None:
        line = raw.split("//", 1)[0].strip()
        if not line:
            return None
        parts = line.split()
        head = parts[0]

        if head in ARITHMETIC_COMMANDS:
            if len(parts) != 1:
                raise self._fail(lineno, line, f"{head} 不接受參數")
            return Command(CommandType.C_ARITHMETIC, head, None, lineno, line)

        if head in ("push", "pop"):
            if len(parts) != 3:
                raise self._fail(lineno, line, f"{head} 需要「區段 索引」兩個參數")
            segment = parts[1]
            if segment not in SEGMENTS:
                raise self._fail(lineno, line, f"未知的記憶體區段「{segment}」")
            index = self._parse_index(parts[2], lineno, line)
            if segment == "pointer" and index not in (0, 1):
                raise self._fail(lineno, line, "pointer 的索引只能是 0（THIS）或 1（THAT）")
            cmd_type = CommandType.C_PUSH if head == "push" else CommandType.C_POP
            return Command(cmd_type, segment, index, lineno, line)

        if head in ("label", "goto", "if-goto"):
            if len(parts) != 2:
                raise self._fail(lineno, line, f"{head} 需要一個標籤名稱")
            name = parts[1]
            self._check_symbol(name, lineno, line)
            cmd_type = {
                "label": CommandType.C_LABEL,
                "goto": CommandType.C_GOTO,
                "if-goto": CommandType.C_IF,
            }[head]
            return Command(cmd_type, name, None, lineno, line)

        if head in ("function", "call"):
            if len(parts) != 3:
                raise self._fail(lineno, line, f"{head} 需要「函式名 數量」兩個參數")
            name = parts[1]
            self._check_symbol(name, lineno, line)
            count = self._parse_index(parts[2], lineno, line)
            cmd_type = CommandType.C_FUNCTION if head == "function" else CommandType.C_CALL
            return Command(cmd_type, name, count, lineno, line)

        if head == "return":
            if len(parts) != 1:
                raise self._fail(lineno, line, "return 不接受參數")
            return Command(CommandType.C_RETURN, None, None, lineno, line)

        raise self._fail(lineno, line, f"未知的 VM 指令「{head}」")
