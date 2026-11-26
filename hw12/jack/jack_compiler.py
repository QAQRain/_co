#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Jack 編譯器（Nand2Tetris Project 10）

把 .jack 翻譯成 .vm。文法剖析的骨架與第九章相同，但這裡只輸出
VM 指令，不再輸出 XML。第九章的 jack_analyzer.py 保留原樣，
可隨時重跑與官方 XML 比對。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TextIO

from jack_error import JackError
from jack_tokenizer import JackTokenizer, Token, TokenType
from jack_symbol_table import ARG, FIELD, KIND_TO_SEGMENT, STATIC, VAR, SymbolTable
from vm_writer import VmWriter

STATEMENT_KEYWORDS = {"let", "if", "while", "do", "return"}
OP_SYMBOLS = {"+", "-", "*", "/", "&", "|", "<", ">", "="}
UNARY_OPS = {"-", "~"}


class CompilationEngine:
    """一邊剖析 Jack，一邊呼叫 VmWriter 輸出 VM 程式碼。"""

    def __init__(
        self,
        tokenizer: JackTokenizer,
        writer: VmWriter,
        class_name: str,
    ) -> None:
        self.t = tokenizer
        self.writer = writer
        self.class_name = class_name
        self.symbols = SymbolTable()
        self._if_counter = 0
        self._while_counter = 0
        self._return_type = "void"
        self._is_constructor = False

    # ------------------------------------------------------------ 基礎 Helper

    def _peek(self) -> Token | None:
        return self.t.peek()

    def _value(self) -> str | None:
        token = self.t.peek()
        return token.value if token else None

    def _error(self, message: str, token: Token | None = None) -> JackError:
        chosen = token if token is not None else self.t.peek()
        if chosen is None:
            return JackError(0, "檔案結尾", message, self.t.path)
        return JackError(chosen.lineno, chosen.value, message, self.t.path)

    def _expect(self, kind: TokenType, value: str | None = None) -> Token:
        token = self.t.peek()
        if token is None:
            raise self._error(f"預期 {kind.value}，但已到檔案結尾")
        if token.type is not kind or (value is not None and token.value != value):
            want = value if value is not None else kind.value
            raise self._error(f"預期「{want}」，但得到「{token.value}」", token)
        return self.t.advance()

    def _expect_keyword(self, value: str) -> Token:
        return self._expect(TokenType.KEYWORD, value)

    def _expect_symbol(self, value: str) -> Token:
        return self._expect(TokenType.SYMBOL, value)

    def _expect_identifier(self) -> Token:
        return self._expect(TokenType.IDENTIFIER)

    def _read_type(self) -> str:
        token = self.t.peek()
        if token is None:
            raise self._error("預期資料型別")
        if (
            token.type is TokenType.KEYWORD
            and token.value in ("int", "char", "boolean", "void")
        ) or token.type is TokenType.IDENTIFIER:
            return self.t.advance().value
        raise self._error("預期 int、char、boolean、void 或類別名稱", token)

    # ------------------------------------------------------------ 變數 Helper

    def _push_var(self, name: str) -> None:
        kind = self.symbols.kind_of(name)
        if kind is None:
            raise self._error(f"未宣告的變數「{name}」")
        index = self.symbols.index_of(name)
        self.writer.write_push(KIND_TO_SEGMENT[kind], index or 0)

    def _pop_var(self, name: str) -> None:
        kind = self.symbols.kind_of(name)
        if kind is None:
            raise self._error(f"未宣告的變數「{name}」")
        index = self.symbols.index_of(name)
        self.writer.write_pop(KIND_TO_SEGMENT[kind], index or 0)

    # ------------------------------------------------------------ 頂層

    def compile_class(self) -> None:
        self._expect_keyword("class")
        self.class_name = self._expect_identifier().value
        self._expect_symbol("{")

        while self._value() in ("static", "field"):
            self.compile_class_var_dec()
        while self._value() in ("constructor", "function", "method"):
            self.compile_subroutine()

        self._expect_symbol("}")
        extra = self.t.peek()
        if extra is not None:
            raise self._error("類別結束後還有剩餘的 token", extra)

    def compile_class_var_dec(self) -> None:
        kind = self.t.advance().value
        var_type = self._read_type()
        name = self._expect_identifier().value
        self.symbols.define(name, var_type, kind)
        while self._value() == ",":
            self._expect_symbol(",")
            name = self._expect_identifier().value
            self.symbols.define(name, var_type, kind)
        self._expect_symbol(";")

    def compile_subroutine(self) -> None:
        kind = self.t.advance().value
        self._is_constructor = kind == "constructor"
        self._return_type = self._read_type()
        name = self._expect_identifier().value

        self.symbols.start_subroutine()
        self._expect_symbol("(")
        self.compile_parameter_list()
        self._expect_symbol(")")
        self._expect_symbol("{")

        while self._value() == "var":
            self.compile_var_dec()

        n_locals = self.symbols.var_count(VAR)
        self.writer.write_function(f"{self.class_name}.{name}", n_locals)

        if kind == "method":
            self.writer.write_push("argument", 0)
            self.writer.write_pop("pointer", 0)
        elif kind == "constructor":
            self.writer.write_push("constant", self.symbols.var_count(FIELD))
            self.writer.write_call("Memory.alloc", 1)
            self.writer.write_pop("pointer", 0)

        self.compile_statements()
        self._expect_symbol("}")

    def compile_parameter_list(self) -> None:
        if self._value() != ")":
            var_type = self._read_type()
            name = self._expect_identifier().value
            self.symbols.define(name, var_type, ARG)
            while self._value() == ",":
                self._expect_symbol(",")
                var_type = self._read_type()
                name = self._expect_identifier().value
                self.symbols.define(name, var_type, ARG)

    def compile_var_dec(self) -> None:
        self._expect_keyword("var")
        var_type = self._read_type()
        name = self._expect_identifier().value
        self.symbols.define(name, var_type, VAR)
        while self._value() == ",":
            self._expect_symbol(",")
            name = self._expect_identifier().value
            self.symbols.define(name, var_type, VAR)
        self._expect_symbol(";")

    # ------------------------------------------------------------ 陳述式

    def compile_statements(self) -> None:
        while self._value() in STATEMENT_KEYWORDS:
            value = self._value()
            if value == "let":
                self.compile_let()
            elif value == "if":
                self.compile_if()
            elif value == "while":
                self.compile_while()
            elif value == "do":
                self.compile_do()
            elif value == "return":
                self.compile_return()

    def compile_let(self) -> None:
        self._expect_keyword("let")
        name = self._expect_identifier().value

        if self._value() == "[":
            self._expect_symbol("[")
            self._push_var(name)
            self.compile_expression()
            self._expect_symbol("]")
            self.writer.write_arithmetic("add")
            self._expect_symbol("=")
            self.compile_expression()
            self.writer.write_pop("temp", 0)
            self.writer.write_pop("pointer", 1)
            self.writer.write_pop("that", 0)
            self._expect_symbol(";")
            return

        self._expect_symbol("=")
        self.compile_expression()
        self._pop_var(name)
        self._expect_symbol(";")

    def compile_if(self) -> None:
        self._if_counter += 1
        number = self._if_counter
        true_label = f"IF_TRUE${number}"
        false_label = f"IF_FALSE${number}"
        end_label = f"IF_END${number}"

        self._expect_keyword("if")
        self._expect_symbol("(")
        self.compile_expression()
        self._expect_symbol(")")
        self.writer.write_if(true_label)
        self.writer.write_goto(false_label)
        self.writer.write_label(true_label)
        self._expect_symbol("{")
        self.compile_statements()
        self._expect_symbol("}")
        self.writer.write_goto(end_label)
        self.writer.write_label(false_label)

        if self._value() == "else":
            self._expect_keyword("else")
            self._expect_symbol("{")
            self.compile_statements()
            self._expect_symbol("}")

        self.writer.write_label(end_label)

    def compile_while(self) -> None:
        self._while_counter += 1
        number = self._while_counter
        start_label = f"WHILE${number}"
        end_label = f"WHILE_END${number}"

        self._expect_keyword("while")
        self.writer.write_label(start_label)
        self._expect_symbol("(")
        self.compile_expression()
        self._expect_symbol(")")
        self.writer.write_arithmetic("not")
        self.writer.write_if(end_label)
        self._expect_symbol("{")
        self.compile_statements()
        self._expect_symbol("}")
        self.writer.write_goto(start_label)
        self.writer.write_label(end_label)

    def compile_do(self) -> None:
        self._expect_keyword("do")
        self._compile_call()
        self.writer.write_pop("temp", 0)
        self._expect_symbol(";")

    def compile_return(self) -> None:
        self._expect_keyword("return")
        if self._value() != ";":
            self.compile_expression()
        elif self._is_constructor:
            self.writer.write_push("pointer", 0)
        elif self._return_type == "void":
            self.writer.write_push("constant", 0)
        self._expect_symbol(";")
        self.writer.write_return()

    # ------------------------------------------------------------ 呼叫與運算式

    def _compile_call(self) -> None:
        first = self._expect_identifier().value
        n_args = 0

        if self._value() == ".":
            self._expect_symbol(".")
            second = self._expect_identifier().value
            kind = self.symbols.kind_of(first)
            if kind is None:
                full_name = f"{first}.{second}"
            else:
                self._push_var(first)
                full_name = f"{self.symbols.type_of(first)}.{second}"
                n_args = 1
        else:
            self.writer.write_push("pointer", 0)
            full_name = f"{self.class_name}.{first}"
            n_args = 1

        self._expect_symbol("(")
        n_args += self.compile_expression_list()
        self._expect_symbol(")")
        self.writer.write_call(full_name, n_args)

    def compile_expression(self) -> None:
        self.compile_term()
        while self._value() in OP_SYMBOLS:
            op = self.t.advance().value
            self.compile_term()
            if op == "+":
                self.writer.write_arithmetic("add")
            elif op == "-":
                self.writer.write_arithmetic("sub")
            elif op == "&":
                self.writer.write_arithmetic("and")
            elif op == "|":
                self.writer.write_arithmetic("or")
            elif op == "=":
                self.writer.write_arithmetic("eq")
            elif op == ">":
                self.writer.write_arithmetic("gt")
            elif op == "<":
                self.writer.write_arithmetic("lt")
            elif op == "*":
                self.writer.write_call("Math.multiply", 2)
            elif op == "/":
                self.writer.write_call("Math.divide", 2)

    def compile_term(self) -> None:
        token = self.t.peek()
        if token is None:
            raise self._error("預期 term，但已到檔案結尾")

        if token.type is TokenType.INT_CONST:
            self.writer.write_push("constant", int(self.t.advance().value))
            return

        if token.type is TokenType.STRING_CONST:
            value = self.t.advance().value
            self.writer.write_push("constant", len(value))
            self.writer.write_call("String.new", 1)
            for char in value:
                self.writer.write_push("constant", ord(char))
                self.writer.write_call("String.appendChar", 2)
            return

        if token.type is TokenType.KEYWORD:
            value = self.t.advance().value
            if value == "true":
                self.writer.write_push("constant", 0)
                self.writer.write_arithmetic("not")
            elif value in ("false", "null"):
                self.writer.write_push("constant", 0)
            elif value == "this":
                self.writer.write_push("pointer", 0)
            else:
                raise self._error(f"關鍵字「{value}」不能出現在運算式中", token)
            return

        if token.type is TokenType.SYMBOL and token.value == "(":
            self._expect_symbol("(")
            self.compile_expression()
            self._expect_symbol(")")
            return

        if token.type is TokenType.SYMBOL and token.value in UNARY_OPS:
            op = self.t.advance().value
            self.compile_term()
            self.writer.write_arithmetic("neg" if op == "-" else "not")
            return

        if token.type is TokenType.IDENTIFIER:
            self._expect_identifier()
            following = self._value()
            if following == "[":
                self._expect_symbol("[")
                self._push_var(token.value)
                self.compile_expression()
                self._expect_symbol("]")
                self.writer.write_arithmetic("add")
                self.writer.write_pop("pointer", 1)
                self.writer.write_push("that", 0)
                return
            if following in ("(", "."):
                self._compile_call_at(token.value)
                return
            self._push_var(token.value)
            return

        raise self._error("無法辨識的 term", token)

    def _compile_call_at(self, first: str) -> None:
        """compile_term 已經吃掉第一個 identifier，這裡接著處理呼叫。"""
        n_args = 0
        if self._value() == ".":
            self._expect_symbol(".")
            second = self._expect_identifier().value
            kind = self.symbols.kind_of(first)
            if kind is None:
                full_name = f"{first}.{second}"
            else:
                self._push_var(first)
                full_name = f"{self.symbols.type_of(first)}.{second}"
                n_args = 1
        else:
            self.writer.write_push("pointer", 0)
            full_name = f"{self.class_name}.{first}"
            n_args = 1

        self._expect_symbol("(")
        n_args += self.compile_expression_list()
        self._expect_symbol(")")
        self.writer.write_call(full_name, n_args)

    def compile_expression_list(self) -> int:
        count = 0
        if self._value() != ")":
            self.compile_expression()
            count = 1
            while self._value() == ",":
                self._expect_symbol(",")
                self.compile_expression()
                count += 1
        return count


def compile_file(
    source: str | Path,
    output: str | Path | None = None,
    verbose: bool = False,
) -> dict:
    """翻譯單一 .jack，回傳統計資訊。"""
    source = Path(source)
    if not source.is_file():
        raise FileNotFoundError(f"找不到檔案：{source}")

    output_path = Path(output) if output else source.with_suffix(".vm")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    tokenizer = JackTokenizer(source)
    with open(output_path, "w", encoding="ascii", newline="\n") as file:
        writer = VmWriter(file)
        engine = CompilationEngine(tokenizer, writer, source.stem)
        engine.compile_class()

    stats = {
        "source": source,
        "output": output_path,
        "tokens": len(tokenizer),
        "vm_lines": writer.line_count,
    }

    if verbose:
        print(f"來源      ：{stats['source']}")
        print(f"輸出      ：{stats['output']}")
        print(f"token 數  ：{stats['tokens']}")
        print(f"VM 指令數 ：{stats['vm_lines']}")

    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="jack_compiler.py",
        description="Nand2Tetris Jack 編譯器：把 .jack 翻譯成 .vm",
    )
    parser.add_argument("source", nargs="?", help=".jack 檔或包含 .jack 的資料夾")
    parser.add_argument("output", nargs="?", help="輸出的 .vm 路徑（預設同名）")
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
        targets = sorted(source.glob("*.jack"))
        if not targets:
            print(f"錯誤：{source} 裡沒有 .jack 檔", file=sys.stderr)
            return 2
    else:
        targets = [source]

    failed = 0
    for target in targets:
        try:
            stats = compile_file(target, args.output, args.verbose)
        except JackError as exc:
            print(f"[失敗] {target}：{exc}", file=sys.stderr)
            failed += 1
            continue
        except (FileNotFoundError, ValueError, OSError) as exc:
            print(f"[失敗] {exc}", file=sys.stderr)
            failed += 1
            continue

        if not args.verbose:
            print(
                f"[完成] {stats['source']} → {stats['output']}"
                f"（{stats['vm_lines']} 個 VM 指令）"
            )

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
