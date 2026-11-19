#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM 翻譯器的錯誤型別。"""

from __future__ import annotations

from pathlib import Path


class VmError(Exception):
    """帶行號、原始碼片段與檔名的翻譯錯誤。"""

    def __init__(
        self,
        lineno: int,
        source: str,
        message: str,
        path: Path | None = None,
    ) -> None:
        self.lineno = lineno
        self.source = source
        self.message = message
        self.path = path
        prefix = f"{path} " if path is not None else ""
        super().__init__(f"{prefix}第 {lineno} 行「{source}」：{message}")
