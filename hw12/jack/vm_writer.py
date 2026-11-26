#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VmWriter：第十章的 VM 指令輸出後端。

只負責把語意轉成 .vm 文字，不負責 Jack 文法；文法交給 jack_compiler.py。
"""

from __future__ import annotations

from typing import TextIO

SEGMENTS = {"constant", "local", "argument", "this", "that", "temp", "pointer", "static"}
ARITHMETICS = {"add", "sub", "neg", "eq", "gt", "lt", "and", "or", "not"}


class VmWriter:
    """把 VM 指令寫入開啟的文字檔。"""

    def __init__(self, file: TextIO) -> None:
        self.file = file
        self.line_count = 0

    def _emit(self, line: str) -> None:
        self.file.write(line + "\n")
        self.line_count += 1

    def write_push(self, segment: str, index: int) -> None:
        if segment not in SEGMENTS:
            raise ValueError(f"未知的 push 區段：{segment}")
        self._emit(f"push {segment} {index}")

    def write_pop(self, segment: str, index: int) -> None:
        if segment not in SEGMENTS:
            raise ValueError(f"未知的 pop 區段：{segment}")
        self._emit(f"pop {segment} {index}")

    def write_arithmetic(self, command: str) -> None:
        if command not in ARITHMETICS:
            raise ValueError(f"未知的算術指令：{command}")
        self._emit(command)

    def write_label(self, label: str) -> None:
        self._emit(f"label {label}")

    def write_goto(self, label: str) -> None:
        self._emit(f"goto {label}")

    def write_if(self, label: str) -> None:
        self._emit(f"if-goto {label}")

    def write_call(self, name: str, n_args: int) -> None:
        self._emit(f"call {name} {n_args}")

    def write_function(self, name: str, n_locals: int) -> None:
        self._emit(f"function {name} {n_locals}")

    def write_return(self) -> None:
        self._emit("return")
