#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""煙霧測試：把 tests/ 底下的 .vm 翻譯成 .asm，再交給組譯器組成 .hack。

用法：
    python tests/run_tests.py

真正的語意驗證請用官方 CPUEmulator / VMEmulator 執行產生的 .asm 或 .hack。
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VM_ROOT = HERE.parent
ASSEMBLER_ROOT = VM_ROOT.parent / "assembler"

sys.path.insert(0, str(VM_ROOT))
sys.path.insert(0, str(ASSEMBLER_ROOT))

import assembler  # noqa: E402
import vm_translator  # noqa: E402


def check_output(asm_path: Path) -> int:
    """組譯 .asm，並確認每條機器碼都是 16 個 0/1。"""
    stats = assembler.assemble_file(asm_path)
    lines = stats["output"].read_text(encoding="ascii").splitlines()
    if not lines:
        raise AssertionError("沒有產生任何機器碼")
    for index, line in enumerate(lines, start=1):
        if len(line) != 16 or set(line) - {"0", "1"}:
            raise AssertionError(f"第 {index} 行不是 16 位元機器碼：{line}")
    return len(lines)


def main() -> int:
    sources = sorted(HERE.rglob("*.vm"))
    if not sources:
        print("找不到 .vm 測試檔")
        return 2

    passed = 0
    failed = 0

    # 單檔模式
    for vm in sources:
        label = vm.relative_to(HERE)
        try:
            stats = vm_translator.translate_source(vm)
            count = check_output(stats["output"])
        except Exception as exc:
            print(f"[失敗] {label}：{exc}")
            failed += 1
            continue
        print(f"[通過] {label}（{stats['commands']} 個 VM 指令 → {count} 個機器碼）")
        passed += 1

    # 資料夾合併模式
    directories = sorted({path.parent for path in sources})
    for directory in directories:
        label = directory.relative_to(HERE)
        try:
            stats = vm_translator.translate_source(directory)
            count = check_output(stats["output"])
        except Exception as exc:
            print(f"[失敗] {label}/（合併）：{exc}")
            failed += 1
            continue
        boot = "，含啟動程序" if stats["bootstrap"] else ""
        print(
            f"[通過] {label}/（合併 {stats['files']} 個檔案 → "
            f"{count} 個機器碼{boot}）"
        )
        passed += 1

    print(f"\n結果：{passed} 通過、{failed} 失敗")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
