#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Jack 分析器（Nand2Tetris Project 9）

把 .jack 轉成兩份 XML：
  - MainT.xml：token 清單（驗 JackTokenizer）
  - Main.xml ：解析樹（驗 CompilationEngine）

第十章會在同一個流程上加入 vm_writer.py，改為輸出 .vm。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TextIO

from compilation_engine import CompilationEngine
from jack_error import JackError
from jack_tokenizer import JackTokenizer, token_to_xml


def write_token_xml(tokenizer: JackTokenizer, file: TextIO) -> int:
    """輸出 token 清單，回傳行數。"""
    count = 0
    for token in tokenizer.tokens:
        file.write(token_to_xml(token) + "\n")
        count += 1
    return count


def _open_output(path: Path) -> TextIO:
    path.parent.mkdir(parents=True, exist_ok=True)
    return open(path, "w", encoding="utf-8", newline="\n")


def analyze_file(
    source: str | Path,
    output: str | Path | None = None,
    tokens_output: str | Path | None = None,
    tokens_only: bool = False,
    tree_only: bool = False,
    verbose: bool = False,
) -> dict:
    """分析單一 .jack，回傳統計資訊。"""
    source = Path(source)
    if not source.is_file():
        raise FileNotFoundError(f"找不到檔案：{source}")
    if tokens_only and tree_only:
        raise ValueError("不能同時指定 tokens_only 與 tree_only")

    stem = Path(output).with_suffix("") if output else source.with_suffix("")
    tree_path = Path(output) if output else Path(str(stem) + ".xml")
    tokens_path = Path(tokens_output) if tokens_output else Path(str(stem) + "T.xml")

    token_count = len(JackTokenizer(source))
    tree_lines = 0
    token_lines = 0

    if not tree_only:
        tokenizer = JackTokenizer(source)
        with _open_output(tokens_path) as file:
            token_lines = write_token_xml(tokenizer, file)

    if not tokens_only:
        tokenizer = JackTokenizer(source)
        with _open_output(tree_path) as file:
            engine = CompilationEngine(tokenizer, file)
            engine.compile_class()
        tree_lines = count_lines(tree_path)

    stats = {
        "source": source,
        "tokens_xml": None if tree_only else tokens_path,
        "tree_xml": None if tokens_only else tree_path,
        "tokens": token_count,
        "token_lines": token_lines,
        "tree_lines": tree_lines,
    }

    if verbose:
        print(f"來源      ：{stats['source']}")
        print(f"token XML ：{stats['tokens_xml'] or '（略過）'}")
        print(f"解析樹 XML：{stats['tree_xml'] or '（略過）'}")
        print(f"token 數  ：{stats['tokens']}")
        print(f"token 行數：{stats['token_lines']}")
        print(f"解析樹行數：{stats['tree_lines']}")

    return stats


def count_lines(path: Path) -> int:
    """讀回檔案計算行數（輸出串流不一定能可靠 tell）。"""
    text = path.read_text(encoding="utf-8")
    return len(text.splitlines())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="jack_analyzer.py",
        description="Nand2Tetris Jack 分析器：把 .jack 轉成 token XML 與解析樹 XML",
    )
    parser.add_argument("source", nargs="?", help=".jack 檔或包含 .jack 的資料夾")
    parser.add_argument("output", nargs="?", help="解析樹 XML 的輸出路徑（預設同名）")
    parser.add_argument("-t", "--tokens-only", action="store_true", help="只輸出 token XML")
    parser.add_argument("--tree-only", action="store_true", help="只輸出解析樹 XML")
    parser.add_argument("--tokens-output", help="token XML 的輸出路徑")
    parser.add_argument("-v", "--verbose", action="store_true", help="顯示統計資訊")
    args = parser.parse_args(argv)

    if not args.source:
        parser.print_help()
        return 0

    source = Path(args.source)
    if source.is_dir():
        if args.output or args.tokens_output:
            print("錯誤：來源是資料夾時不能指定輸出檔", file=sys.stderr)
            return 2
        targets = sorted(source.glob("*.jack"))
        if not targets:
            print(f"錯誤：{source} 裡沒有 .jack 檔", file=sys.stderr)
            return 2
    else:
        targets = [source]

    failed = 0
    for target in targets:
        try:
            stats = analyze_file(
                target,
                args.output,
                args.tokens_output,
                args.tokens_only,
                args.tree_only,
                args.verbose,
            )
        except JackError as exc:
            print(f"[失敗] {target}：{exc}", file=sys.stderr)
            failed += 1
            continue
        except (FileNotFoundError, ValueError, OSError) as exc:
            print(f"[失敗] {exc}", file=sys.stderr)
            failed += 1
            continue

        if not args.verbose:
            made = [str(p) for p in (stats["tokens_xml"], stats["tree_xml"]) if p]
            print(f"[完成] {target} → {'、'.join(made)}（{stats['tokens']} 個 token）")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
