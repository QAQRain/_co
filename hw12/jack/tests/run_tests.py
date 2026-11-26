#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""測試 tests/ 底下所有 .jack。

若旁邊有官方的 Xxx.xml 與 XxxT.xml，就逐行比對；
沒有預期檔時，只檢查輸出是否為成對的 XML。

用法：
    python tests/run_tests.py
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

import jack_analyzer  # noqa: E402


def compare_files(actual: Path, expected: Path) -> str | None:
    """回傳 None 代表一致或沒有預期檔，否則回傳差異說明。"""
    if not expected.exists():
        return None
    got = actual.read_text(encoding="utf-8").splitlines()
    want = expected.read_text(encoding="utf-8-sig").splitlines()
    if got == want:
        return None
    for index, (left, right) in enumerate(zip(got, want), start=1):
        if left != right:
            return f"第 {index} 行：得到「{left}」，預期「{right}」"
    return f"行數不同：得到 {len(got)} 行，預期 {len(want)} 行"


def check_balanced(path: Path) -> str | None:
    """確認所有 XML 標籤都有成對出現。"""
    text = path.read_text(encoding="utf-8")
    opens = Counter(re.findall(r"<([A-Za-z]+)>", text))
    closes = Counter(re.findall(r"</([A-Za-z]+)>", text))
    if opens != closes:
        return f"標籤不成對：開 {dict(opens)}、閉 {dict(closes)}"
    if not text.strip():
        return "輸出是空的"
    return None


def main() -> int:
    sources = sorted(HERE.rglob("*.jack"))
    if not sources:
        print("找不到 .jack 測試檔")
        return 2

    passed = 0
    failed = 0

    for jack in sources:
        stem = jack.with_suffix("")
        my_tree = Path(str(stem) + "_my.xml")
        my_tokens = Path(str(stem) + "_myT.xml")
        label = jack.relative_to(HERE)

        try:
            stats = jack_analyzer.analyze_file(
                jack, output=my_tree, tokens_output=my_tokens
            )
            tree_error = check_balanced(my_tree)
            token_error = check_balanced(my_tokens)
            if tree_error or token_error:
                raise AssertionError(tree_error or token_error)

            tree_diff = compare_files(my_tree, Path(str(stem) + ".xml"))
            token_diff = compare_files(my_tokens, Path(str(stem) + "T.xml"))
            if tree_diff or token_diff:
                raise AssertionError(tree_diff or token_diff)
        except Exception as exc:
            print(f"[失敗] {label}：{exc}")
            failed += 1
            continue

        print(
            f"[通過] {label}（{stats['tokens']} 個 token、"
            f"解析樹 {stats['tree_lines']} 行）"
        )
        passed += 1

    print(f"\n結果：{passed} 通過、{failed} 失敗")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
