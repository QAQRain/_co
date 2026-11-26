#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第十章煙霧測試：把所有 .jack 轉成 .vm → .asm → .hack。

若旁邊有官方預期的 Xxx.vm，會逐行比對；沒有時只檢查
翻譯與組譯是否成功、機器碼是否為 16 位元。

用法：
    python tests/run_tests_ch10.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FOR_CO = ROOT.parent

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(FOR_CO / "vm"))
sys.path.insert(0, str(FOR_CO / "assembler"))

import assembler  # noqa: E402
import jack_compiler  # noqa: E402
import vm_translator  # noqa: E402


def check_hack(path: Path) -> int:
    lines = path.read_text(encoding="ascii").splitlines()
    if not lines:
        raise AssertionError("沒有產生機器碼")
    for index, line in enumerate(lines, start=1):
        if len(line) != 16 or set(line) - {"0", "1"}:
            raise AssertionError(f"第 {index} 行不是 16 位元：{line}")
    return len(lines)


def normalize_labels(lines: list[str]) -> list[str]:
    """標籤流水號各家Compiler不同，比對時統一成正規形式。"""
    result: list[str] = []
    for line in lines:
        parts = line.split()
        if len(parts) == 2 and parts[0] in ("label", "goto", "if-goto"):
            parts[1] = re.sub(r"\$?\d+$", "$#", parts[1])
            line = " ".join(parts)
        result.append(line)
    return result


def compare_vm(actual: Path, expected: Path) -> str | None:
    if not expected.exists():
        return None
    got = normalize_labels(actual.read_text(encoding="ascii").splitlines())
    want = normalize_labels(expected.read_text(encoding="utf-8-sig").splitlines())
    if got == want:
        return None
    for index, (left, right) in enumerate(zip(got, want), start=1):
        if left != right:
            return f"第 {index} 行：得到「{left}」，預期「{right}」"
    return f"行數不同：得到 {len(got)}，預期 {len(want)}"


def main() -> int:
    sources = sorted(HERE.rglob("*.jack"))
    if not sources:
        print("找不到 .jack 測試檔")
        return 2

    passed = 0
    failed = 0

    for jack in sources:
        stem = jack.with_suffix("")
        my_vm = Path(str(stem) + "_my.vm")
        my_asm = Path(str(stem) + "_my.asm")
        label = jack.relative_to(HERE)

        try:
            vm_stats = jack_compiler.compile_file(jack, output=my_vm)
            asm_stats = vm_translator.translate_source(
                my_vm, output=my_asm, bootstrap=False
            )
            hack_stats = assembler.assemble_file(asm_stats["output"])
            machine_count = check_hack(hack_stats["output"])
            diff = compare_vm(my_vm, Path(str(stem) + ".vm"))
            if diff:
                raise AssertionError(diff)
        except Exception as exc:
            print(f"[失敗] {label}：{exc}")
            failed += 1
            continue

        print(
            f"[通過] {label}（{vm_stats['vm_lines']} 個 VM 指令 → "
            f"{machine_count} 個機器碼）"
        )
        passed += 1

    print(f"\n結果：{passed} 通過、{failed} 失敗")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
