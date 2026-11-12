#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hack C 指令的三張對照表（dest / comp / jump）。

命名為 hack_code 而非 code，是為了避免蓋掉 Python 標準庫的 code 模組
（除錯工具 pdb 會用到它）。

每個函式都把組合語言片段轉成對應的二進位字串，
查不到就丟 ValueError，由 assembler.py 加上行號後回報。
"""

# dest：3 bits（d1 d2 d3）
DEST_TABLE = {
    "": "000",
    "M": "001",
    "D": "010",
    "MD": "011",
    "A": "100",
    "AM": "101",
    "AD": "110",
    "AMD": "111",
}

# jump：3 bits（j1 j2 j3）
JUMP_TABLE = {
    "": "000",
    "JGT": "001",
    "JEQ": "010",
    "JGE": "011",
    "JLT": "100",
    "JNE": "101",
    "JLE": "110",
    "JMP": "111",
}

# comp：7 bits（a c1 c2 c3 c4 c5 c6）
# a=0 表示運算只用到 A；a=1 表示運算用到 M（A 所指位址的記憶體內容）
COMP_TABLE = {
    "0": "0101010",
    "1": "0111111",
    "-1": "0111010",
    "D": "0001100",
    "A": "0110000",
    "M": "1110000",
    "!D": "0001101",
    "!A": "0110001",
    "!M": "1110001",
    "-D": "0001111",
    "-A": "0110011",
    "-M": "1110011",
    "D+1": "0011111",
    "A+1": "0110111",
    "M+1": "1110111",
    "D-1": "0001110",
    "A-1": "0110010",
    "M-1": "1110010",
    "D+A": "0000010",
    "D+M": "1000010",
    "D-A": "0010011",
    "D-M": "1010011",
    "A-D": "0000111",
    "M-D": "1000111",
    "D&A": "0000000",
    "D&M": "1000000",
    "D|A": "0010101",
    "D|M": "1010101",
}


def _lookup(table: dict, key: str, field: str) -> str:
    try:
        return table[key]
    except KeyError:
        legal = "、".join(sorted(k for k in table if k))
        raise ValueError(f"未知的 {field}「{key}」，合法值：{legal}") from None


def dest_bits(dest: str) -> str:
    """dest 欄位 → 3 bits。空字串代表不儲存。"""
    return _lookup(DEST_TABLE, dest, "dest")


def jump_bits(jump: str) -> str:
    """jump 欄位 → 3 bits。空字串代表不跳躍。"""
    return _lookup(JUMP_TABLE, jump, "jump")


def comp_bits(comp: str) -> str:
    """comp 欄位 → 7 bits（含 a 位元）。"""
    return _lookup(COMP_TABLE, comp, "comp")
