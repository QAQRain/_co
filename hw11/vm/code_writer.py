#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM CodeWriter：把 Parser 解析出的指令轉成 Hack 組合語言。

刻意不模仿官方翻譯器的暫存器與標籤命名，只要語意正確、能通過
自己的 assembler.py 即可。內部使用 R13 當記憶體目的位址暫存器、
R14 當返回地址暫存器。
"""

from __future__ import annotations

from textwrap import dedent
from typing import TextIO

from vm_parser import Command, CommandType

SEGMENT_BASE = {
    "local": "LCL",
    "argument": "ARG",
    "this": "THIS",
    "that": "THAT",
}
POINTER_SYMBOL = {0: "THIS", 1: "THAT"}


class CodeWriter:
    """產生組語並寫入開啟的文字檔。"""

    def __init__(self, file: TextIO) -> None:
        self._file = file
        self._file_name = ""
        self._current_function = ""
        self._label_counter = 0
        self._eq_counter = 0
        self.line_count = 0

    # ------------------------------------------------------------ 基本輸出

    def _emit(self, *lines: str) -> None:
        for line in lines:
            self._file.write(dedent(line).strip() + "\n")
            self.line_count += 1

    def set_file_name(self, name: str) -> None:
        """設定目前翻譯的 .vm 檔名（不含副檔名），供 static 使用前綴。"""
        self._file_name = name

    # ------------------------------------------------------------ 堆疊 Helper

    def _push_d(self) -> None:
        """把 D 的值推入堆疊（呼叫前 D 必須已經設好）。"""
        self._emit(
            "@SP",
            "A=M",
            "M=D",
            "@SP",
            "M=M+1",
        )

    def _push_constant(self, value: int) -> None:
        self._emit(f"@{value}", "D=A")
        self._push_d()

    def _push_memory(self, lines: list[str]) -> None:
        """給定一連串把值放進 D 的組語，再推入堆疊。"""
        self._emit(*lines)
        self._push_d()

    def _pop_to(self, address_lines: list[str]) -> None:
        """address_lines 執行完後，D 必須是目的位址。"""
        self._emit(*address_lines)
        self._emit(
            "@R13",
            "M=D",
            "@SP",
            "AM=M-1",
            "D=M",
            "@R13",
            "A=M",
            "M=D",
        )

    def _segment_address(self, base: str, index: int) -> list[str]:
        """回傳「D = RAM[base] + index」的組語片段。"""
        return [
            f"@{base}",
            "D=M",
            f"@{index}",
            "D=D+A",
        ]

    # ------------------------------------------------------------ 第 7 章

    def write_arithmetic(self, command: str) -> None:
        if command in ("add", "sub", "and", "or"):
            op = {
                "add": "M=D+M",
                "sub": "M=M-D",
                "and": "M=D&M",
                "or": "M=D|M",
            }[command]
            self._emit("@SP", "AM=M-1", "D=M", "A=A-1", op)
            return

        if command in ("neg", "not"):
            op = {"neg": "M=-M", "not": "M=!M"}[command]
            self._emit("@SP", "A=M-1", op)
            return

        if command in ("eq", "gt", "lt"):
            self._write_comparison(command)
            return

        raise ValueError(f"未知的算術指令：{command}")

    def _write_comparison(self, command: str) -> None:
        self._eq_counter += 1
        number = self._eq_counter
        true_label = f"VM${number}$TRUE"
        end_label = f"VM${number}$END"
        jump = {"eq": "D;JEQ", "gt": "D;JGT", "lt": "D;JLT"}[command]
        self._emit(
            "@SP",
            "AM=M-1",
            "D=M",
            "A=A-1",
            "D=M-D",
            f"@{true_label}",
            jump,
            "@SP",
            "A=M-1",
            "M=0",
            f"@{end_label}",
            "0;JMP",
            f"({true_label})",
            "@SP",
            "A=M-1",
            "M=-1",
            f"({end_label})",
        )

    def write_push_pop(
        self,
        command: CommandType,
        segment: str,
        index: int,
    ) -> None:
        is_push = command is CommandType.C_PUSH

        if segment == "constant":
            if is_push:
                self._push_constant(index)
            else:
                raise ValueError("constant 只能 push，不能 pop")
            return

        if segment in SEGMENT_BASE:
            address = self._segment_address(SEGMENT_BASE[segment], index)
            if is_push:
                self._push_memory([*address, "A=D", "D=M"])
            else:
                self._pop_to(address)
            return

        if segment == "temp":
            address_value = 5 + index
            if is_push:
                self._push_memory([f"@{address_value}", "D=M"])
            else:
                self._pop_to([f"@{address_value}", "D=A"])
            return

        if segment == "pointer":
            symbol = POINTER_SYMBOL[index]
            if is_push:
                self._push_memory([f"@{symbol}", "D=M"])
            else:
                self._pop_to([f"@{symbol}", "D=A"])
            return

        if segment == "static":
            symbol = f"{self._file_name}.{index}"
            if is_push:
                self._push_memory([f"@{symbol}", "D=M"])
            else:
                self._pop_to([f"@{symbol}", "D=A"])
            return

        raise ValueError(f"未知的記憶體區段：{segment}")

    # ------------------------------------------------------------ 第 8 章

    def _scope(self, name: str) -> str:
        """標籤加上函式前綴，避免不同函式的同名標籤衝突。"""
        if self._current_function:
            return f"{self._current_function}${name}"
        return name

    def write_label(self, label: str) -> None:
        self._emit(f"({self._scope(label)})")

    def write_goto(self, label: str) -> None:
        self._emit(f"@{self._scope(label)}", "0;JMP")

    def write_if(self, label: str) -> None:
        self._emit(
            "@SP",
            "AM=M-1",
            "D=M",
            f"@{self._scope(label)}",
            "D;JNE",
        )

    def write_function(self, name: str, n_locals: int) -> None:
        self._current_function = name
        self._emit(f"({name})")
        for _ in range(n_locals):
            self._push_constant(0)

    def write_call(self, name: str, n_args: int) -> None:
        self._label_counter += 1
        return_label = f"{name}$RET${self._label_counter}"

        # push return address
        self._emit(f"@{return_label}", "D=A")
        self._push_d()

        # push LCL, ARG, THIS, THAT（建立堆疊框架）
        for symbol in ("LCL", "ARG", "THIS", "THAT"):
            self._emit(f"@{symbol}", "D=M")
            self._push_d()

        # ARG = SP - 5 - nArgs；LCL = SP；跳到函式
        self._emit(
            "@SP",
            "D=M",
            f"@{5 + n_args}",
            "D=D-A",
            "@ARG",
            "M=D",
            "@SP",
            "D=M",
            "@LCL",
            "M=D",
            f"@{name}",
            "0;JMP",
            f"({return_label})",
        )

    def write_return(self) -> None:
        self._emit(
            "@LCL",
            "D=M",
            "@R13",
            "M=D",
            "@5",
            "A=D-A",
            "D=M",
            "@R14",
            "M=D",
            "@SP",
            "AM=M-1",
            "D=M",
            "@ARG",
            "A=M",
            "M=D",
            "@ARG",
            "D=M",
            "@SP",
            "M=D+1",
        )
        for offset, symbol in (
            (1, "THAT"),
            (2, "THIS"),
            (3, "ARG"),
            (4, "LCL"),
        ):
            self._emit(
                "@R13",
                "M=M-1",
                "A=M",
                "D=M",
                f"@{symbol}",
                "M=D",
            )
        self._emit("@R14", "A=M", "0;JMP")

    def write_bootstrap(self) -> None:
        """設定 SP = 256，再呼叫 Sys.init。"""
        self._emit("@256", "D=A", "@SP", "M=D")
        self.write_call("Sys.init", 0)

    # ------------------------------------------------------------ 分派

    def write_command(self, command: Command) -> None:
        kind = command.type
        if kind is CommandType.C_ARITHMETIC:
            self.write_arithmetic(command.arg1 or "")
        elif kind in (CommandType.C_PUSH, CommandType.C_POP):
            self.write_push_pop(kind, command.arg1 or "", command.arg2 or 0)
        elif kind is CommandType.C_LABEL:
            self.write_label(command.arg1 or "")
        elif kind is CommandType.C_GOTO:
            self.write_goto(command.arg1 or "")
        elif kind is CommandType.C_IF:
            self.write_if(command.arg1 or "")
        elif kind is CommandType.C_FUNCTION:
            self.write_function(command.arg1 or "", command.arg2 or 0)
        elif kind is CommandType.C_CALL:
            self.write_call(command.arg1 or "", command.arg2 or 0)
        elif kind is CommandType.C_RETURN:
            self.write_return()
        else:
            raise ValueError(f"未知的指令類型：{kind}")
