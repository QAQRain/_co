#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""符號表：記錄標籤位址與使用者自訂變數的 RAM 位址。"""

# 組譯器一開始就要認識的預定義符號
PREDEFINED = {
    "SP": 0,
    "LCL": 1,
    "ARG": 2,
    "THIS": 3,
    "THAT": 4,
    "SCREEN": 16384,
    "KBD": 24576,
}
PREDEFINED.update({f"R{i}": i for i in range(16)})


class SymbolTable:
    """名稱 → 位址的字典包裝。

    標籤在 Pass 1 寫入（值是 ROM 位址），
    變數在 Pass 2 寫入（值是從 16 開始的 RAM 位址）。
    """

    def __init__(self) -> None:
        self._table: dict[str, int] = dict(PREDEFINED)

    def add_entry(self, symbol: str, address: int) -> None:
        self._table[symbol] = address

    def contains(self, symbol: str) -> bool:
        return symbol in self._table

    def get_address(self, symbol: str) -> int:
        return self._table[symbol]

    def count_user_symbols(self) -> int:
        """使用者自己定義的符號數量（不含預定義符號）。"""
        return len([k for k in self._table if k not in PREDEFINED])

    def __len__(self) -> int:
        return len(self._table)
