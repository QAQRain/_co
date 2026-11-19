#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nand2Tetris VM 翻譯器（Project 7 + 8）

把 .vm 虛擬機程式翻譯成 Hack 組合語言 .asm，再交給 Project 6 的
assembler.py 組譯成 .hack。

用法：
    python vm_translator.py SimpleAdd.vm
    python vm_translator.py SimpleAdd.vm out.asm
    python vm_translator.py tests/ch8          # 合併資料夾內所有 .vm
    python vm_translator.py tests/ch8 --no-bootstrap
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TextIO

from code_writer import CodeWriter
from vm_error import VmError
from vm_parser import Parser

DEFAULT_BOOTSTRAP_FILE = "Sys.vm"


def translate_file(path: Path, writer: CodeWriter) -> int:
    """翻譯單一 .vm，回傳該檔的 VM 指令數。"""
    parser = Parser(path)
    writer.set_file_name(path.stem)
    for command in parser:
        writer.write_command(command)
    return len(parser)


def _open_output(path: Path) -> TextIO:
    path.parent.mkdir(parents=True, exist_ok=True)
    return open(path, "w", encoding="ascii", newline="\n")


def translate_source(
    source: str | Path,
    output: str | Path | None = None,
    bootstrap: bool | None = None,
    verbose: bool = False,
) -> dict:
    """翻譯單檔或整個資料夾，回傳統計資訊。"""
    source = Path(source)

    if source.is_dir():
        vm_files = sorted(source.glob("*.vm"))
        if not vm_files:
            raise FileNotFoundError(f"資料夾裡沒有 .vm 檔：{source}")
        if output is not None:
            raise ValueError("來源是資料夾時不能指定輸出檔")
        output_path = source.with_suffix(".asm")
        default_bootstrap = any(p.name == DEFAULT_BOOTSTRAP_FILE for p in vm_files)
    else:
        vm_files = [source]
        if not source.is_file():
            raise FileNotFoundError(f"找不到檔案：{source}")
        output_path = Path(output) if output else source.with_suffix(".asm")
        default_bootstrap = False

    use_bootstrap = default_bootstrap if bootstrap is None else bootstrap

    command_count = 0
    with _open_output(output_path) as file:
        writer = CodeWriter(file)
        if use_bootstrap:
            writer.write_bootstrap()
        for vm_file in vm_files:
            command_count += translate_file(vm_file, writer)

    stats = {
        "source": source,
        "output": output_path,
        "files": len(vm_files),
        "commands": command_count,
        "asm_lines": writer.line_count,
        "bootstrap": use_bootstrap,
    }

    if verbose:
        print(f"來源      ：{stats['source']}")
        print(f"輸出      ：{stats['output']}")
        print(f"檔案數    ：{stats['files']}")
        print(f"VM 指令數 ：{stats['commands']}")
        print(f"組語行數  ：{stats['asm_lines']}")
        print(f"啟動程序  ：{'加入' if use_bootstrap else '不加入'}")

    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vm_translator.py",
        description="Nand2Tetris VM 翻譯器：把 .vm 翻譯成 .asm",
    )
    parser.add_argument("source", nargs="?", help=".vm 檔或包含 .vm 的資料夾")
    parser.add_argument("output", nargs="?", help="輸出的 .asm 路徑（預設同名）")
    parser.add_argument(
        "--bootstrap",
        dest="bootstrap",
        action="store_true",
        default=None,
        help="強制加入啟動程序（SP=256 並呼叫 Sys.init）",
    )
    parser.add_argument(
        "--no-bootstrap",
        dest="bootstrap",
        action="store_false",
        help="強制不加入啟動程序",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="顯示統計資訊")
    args = parser.parse_args(argv)

    if not args.source:
        parser.print_help()
        return 0

    try:
        stats = translate_source(args.source, args.output, args.bootstrap, args.verbose)
    except VmError as exc:
        print(f"[失敗] {exc}", file=sys.stderr)
        return 1
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"[失敗] {exc}", file=sys.stderr)
        return 1

    if not args.verbose:
        extra = "（含啟動程序）" if stats["bootstrap"] else ""
        print(
            f"[完成] {stats['source']} → {stats['output']}"
            f"（{stats['files']} 個檔案、{stats['commands']} 個 VM 指令{extra}）"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
