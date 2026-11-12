#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跑 tests/ 底下所有 .asm，與同名的 .expected.hack 逐行比對。

用法：
    python tests/run_tests.py
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import assembler  # noqa: E402


def main() -> int:
    cases = sorted(HERE.glob("*.asm"))
    if not cases:
        print("找不到測試檔")
        return 2

    passed = 0
    failed = 0

    for asm in cases:
        expected_path = asm.with_suffix(".expected.hack")
        if not expected_path.exists():
            print(f"[略過] {asm.name}：沒有 {expected_path.name}")
            continue

        try:
            stats = assembler.assemble_file(asm)
        except assembler.AssemblyError as exc:
            print(f"[失敗] {asm.name}：{exc}")
            failed += 1
            continue

        actual = stats["output"].read_text(encoding="ascii").splitlines()
        expected = expected_path.read_text(encoding="ascii").splitlines()

        if actual == expected:
            print(f"[通過] {asm.name}（{len(actual)} 個指令）")
            passed += 1
            continue

        failed += 1
        print(f"[失敗] {asm.name}")
        if len(actual) != len(expected):
            print(f"       行數不同：產生 {len(actual)} 行，預期 {len(expected)} 行")
        for i in range(max(len(actual), len(expected))):
            got = actual[i] if i < len(actual) else "(缺行)"
            want = expected[i] if i < len(expected) else "(多出行)"
            if got != want:
                print(f"       第 {i + 1} 行：得到 {got}，預期 {want}")

    print(f"\n結果：{passed} 通過、{failed} 失敗")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
