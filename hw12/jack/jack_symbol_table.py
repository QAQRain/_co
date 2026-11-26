#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SymbolTable：管理類別層級與副程式層級的變數。

命名為 jack_symbol_table，是為了避免與 Project 6 assembler 的
symbol_table.py 發生命名衝突（兩者會同時被第十章測試載入）。
"""

from __future__ import annotations

STATIC = "static"
FIELD = "field"
ARG = "arg"
VAR = "var"

KIND_TO_SEGMENT = {
    STATIC: "static",
    FIELD: "this",
    ARG: "argument",
    VAR: "local",
}


class SymbolTable:
    """兩層符號表：class level 與 subroutine level。"""

    def __init__(self) -> None:
        self._class: dict[str, tuple[str, str, int]] = {}
        self._subroutine: dict[str, tuple[str, str, int]] = {}

    def start_subroutine(self) -> None:
        """進入新副程式時清空區域表。"""
        self._subroutine = {}

    def define(self, name: str, var_type: str, kind: str) -> None:
        if kind not in KIND_TO_SEGMENT:
            raise ValueError(f"未知的變數種類：{kind}")
        table = self._class if kind in (STATIC, FIELD) else self._subroutine
        table[name] = (kind, var_type, self.var_count(kind))

    def _find(self, name: str) -> tuple[str, str, int] | None:
        if name in self._subroutine:
            return self._subroutine[name]
        return self._class.get(name)

    def kind_of(self, name: str) -> str | None:
        entry = self._find(name)
        return entry[0] if entry else None

    def type_of(self, name: str) -> str | None:
        entry = self._find(name)
        return entry[1] if entry else None

    def index_of(self, name: str) -> int | None:
        entry = self._find(name)
        return entry[2] if entry else None

    def var_count(self, kind: str) -> int:
        table = self._class if kind in (STATIC, FIELD) else self._subroutine
        return len([entry for entry in table.values() if entry[0] == kind])
