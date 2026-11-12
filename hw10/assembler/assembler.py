#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nand2Tetris Hack 組譯器（Project 6）

把 Hack 組合語言 (.asm) 翻譯成 Hack 機器碼 (.hack)。
每個指令固定 16 bits，輸出檔每行就是 16 個 0/1。

用法：
    python assembler.py tests/Add.asm
    python assembler.py tests/Add.asm out.hack
    python assembler.py tests            # 組譯資料夾內所有 .asm
"""

from __future__ import annotations

import argparse
import string
import sys
from pathlib import Path

from hack_code import comp_bits, dest_bits, jump_bits
from symbol_table import SymbolTable

RAM_START = 16          # 變數從 RAM[16] 開始配（0~15 是 R0~R15）
MAX_ADDRESS = 32767     # 16 bits 扣掉指令型別位元，只剩 15 bits
INSTRUCTION_WIDTH = 16

_SYMBOL_FIRST = set(string.ascii_letters + "_.$:")
_SYMBOL_REST = _SYMBOL_FIRST | set(string.digits)


class AssemblyError(Exception):
    """帶行號與原始碼片段的組譯錯誤。"""

    def __init__(self, lineno: int, source: str, message: str) -> None:
        self.lineno = lineno
        self.source = source
        self.message = message
        super().__init__(f"第 {lineno} 行「{source}」：{message}")


# ---------------------------------------------------------------- 前處理

def clean(raw_line: str) -> str:
    """去掉 // 之後的註解與所有空白；回傳空字串代表這行可跳過。"""
    line = raw_line.split("//", 1)[0]
    return "".join(line.split())


def is_label(text: str) -> bool:
    return text.startswith("(")


def validate_symbol_name(name: str, lineno: int, source: str) -> None:
    """符號只能用英文字母、數字、_ . $ :，且不能以數字開頭。"""
    if not name:
        raise AssemblyError(lineno, source, "符號名稱不可為空")
    if name[0] not in _SYMBOL_FIRST:
        raise AssemblyError(
            lineno, source, f"符號「{name}」不能以「{name[0]}」開頭"
        )
    for ch in name[1:]:
        if ch not in _SYMBOL_REST:
            raise AssemblyError(
                lineno, source, f"符號「{name}」含有非法字元「{ch}」"
            )


def parse_label(text: str, lineno: int) -> str:
    """(LOOP) → LOOP"""
    if not text.endswith(")"):
        raise AssemblyError(lineno, text, "標籤宣告必須以「)」結尾")
    name = text[1:-1]
    validate_symbol_name(name, lineno, text)
    return name


# ---------------------------------------------------------------- 編碼

def encode_c_instruction(lineno: int, text: str) -> str:
    """把 dest=comp;jump 編成 16 bits。dest 與 jump 都可以省略。"""
    dest, jump = "", ""
    body = text

    if "=" in body:
        dest, body = body.split("=", 1)
        if not dest:
            raise AssemblyError(lineno, text, "「=」左邊缺少 dest")
    if ";" in body:
        body, jump = body.split(";", 1)
        if not jump:
            raise AssemblyError(lineno, text, "「;」右邊缺少 jump")

    comp = body
    if not comp:
        raise AssemblyError(lineno, text, "缺少 comp 運算")

    try:
        return (
            "111"
            + comp_bits(comp)
            + dest_bits(dest)
            + jump_bits(jump)
        )
    except ValueError as exc:
        raise AssemblyError(lineno, text, str(exc)) from None


def resolve_operand(
    operand: str,
    lineno: int,
    source: str,
    table: SymbolTable,
    next_ram: int,
) -> tuple[int, bool]:
    """@ 後面的運算元 → (位址, 是否為新配置的變數)。"""
    if not operand:
        raise AssemblyError(lineno, source, "「@」後面缺少運算元")

    # 常數：只接受十進位，且在 0~32767 之間
    if operand.isdigit():
        address = int(operand)
        if address > MAX_ADDRESS:
            raise AssemblyError(
                lineno, source,
                f"常數 {address} 超出範圍（0~{MAX_ADDRESS}）",
            )
        return address, False

    if operand[0].isdigit() or operand[0] in "+-":
        raise AssemblyError(
            lineno, source,
            f"「{operand}」不是合法位址，常數必須是 0~{MAX_ADDRESS} 的十進位整數",
        )

    validate_symbol_name(operand, lineno, source)

    if table.contains(operand):
        return table.get_address(operand), False

    # 沒見過的符號 → 視為變數，配一個 RAM 位址
    if next_ram > MAX_ADDRESS:
        raise AssemblyError(
            lineno, source,
            f"RAM 位址已用完，無法再配置變數「{operand}」",
        )
    table.add_entry(operand, next_ram)
    return next_ram, True


# ---------------------------------------------------------------- 主流程

def read_source_lines(path: Path) -> list[str]:
    if not path.is_file():
        raise FileNotFoundError(f"找不到檔案：{path}")
    # 先試 UTF-8（utf-8-sig 會順便吃掉 BOM）；
    # 舊版 Windows 編輯器存成 ANSI/Big5 時再退回 cp950
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = path.read_text(encoding="cp950", errors="replace")
    return text.splitlines()


def assemble_file(
    source_path: str | Path,
    output_path: str | Path | None = None,
    verbose: bool = False,
) -> dict:
    """組譯單一 .asm 檔，回傳統計資訊。"""
    source_path = Path(source_path)
    raw_lines = read_source_lines(source_path)

    table = SymbolTable()
    program: list[tuple[int, str]] = []   # (行號, 清理後的原始碼)
    rom = 0

    # ---- Pass 1：只建立標籤表，不產生機器碼 ----
    for lineno, raw in enumerate(raw_lines, start=1):
        text = clean(raw)
        if not text:
            continue

        if is_label(text):
            name = parse_label(text, lineno)
            if table.contains(name):
                raise AssemblyError(lineno, text, f"標籤「{name}」重複定義")
            table.add_entry(name, rom)
        else:
            if rom > MAX_ADDRESS:
                raise AssemblyError(
                    lineno, text,
                    f"程式超過 ROM 容量（最多 {MAX_ADDRESS + 1} 個指令）",
                )
            rom += 1

        program.append((lineno, text))

    # ---- Pass 2：產生機器碼 ----
    codes: list[str] = []
    variables: list[str] = []
    next_ram = RAM_START

    for lineno, text in program:
        if is_label(text):
            continue

        if text.startswith("@"):
            address, is_new_variable = resolve_operand(
                text[1:], lineno, text, table, next_ram
            )
            if is_new_variable:
                variables.append(text[1:])
                next_ram += 1
            codes.append(format(address, f"0{INSTRUCTION_WIDTH}b"))
        else:
            codes.append(encode_c_instruction(lineno, text))

    # ---- 輸出 ----
    if output_path is None:
        output_path = source_path.with_suffix(".hack")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="ascii", newline="\n") as fh:
        for code in codes:
            fh.write(code + "\n")

    stats = {
        "source": source_path,
        "output": output_path,
        "instructions": len(codes),
        "labels": len([1 for _, t in program if is_label(t)]),
        "variables": variables,
        "user_symbols": table.count_user_symbols(),
    }

    if verbose:
        print(f"來源      ：{stats['source']}")
        print(f"輸出      ：{stats['output']}")
        print(f"指令數    ：{stats['instructions']}")
        print(f"標籤數    ：{stats['labels']}")
        print(f"變數數    ：{len(variables)}" + (
            f"（{', '.join(variables)}）" if variables else ""))
        print(f"符號總數  ：{stats['user_symbols']}（不含預定義符號）")

    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="assembler.py",
        description="Nand2Tetris Hack 組譯器：把 .asm 翻譯成 .hack",
    )
    parser.add_argument("source", nargs="?", help=".asm 檔或包含 .asm 的資料夾")
    parser.add_argument("output", nargs="?", help="輸出的 .hack 路徑（預設同名）")
    parser.add_argument("-v", "--verbose", action="store_true", help="顯示統計資訊")
    args = parser.parse_args(argv)

    if not args.source:
        parser.print_help()
        return 0

    source = Path(args.source)

    if source.is_dir():
        if args.output:
            print("錯誤：來源是資料夾時不能指定輸出檔", file=sys.stderr)
            return 2
        targets = sorted(source.glob("*.asm"))
        if not targets:
            print(f"錯誤：{source} 裡沒有 .asm 檔", file=sys.stderr)
            return 2
    else:
        targets = [source]

    failed = 0
    for target in targets:
        try:
            stats = assemble_file(target, args.output, verbose=args.verbose)
        except AssemblyError as exc:
            print(f"[失敗] {target}：{exc}", file=sys.stderr)
            failed += 1
            continue
        except (FileNotFoundError, OSError) as exc:
            print(f"[失敗] {exc}", file=sys.stderr)
            failed += 1
            continue

        if not args.verbose:
            print(f"[完成] {stats['source']} → {stats['output']}"
                  f"（{stats['instructions']} 個指令）")

    if failed:
        print(f"共 {failed} 個檔案失敗", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
