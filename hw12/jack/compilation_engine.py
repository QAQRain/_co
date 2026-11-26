#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CompilationEngine：遞迴下降剖析器，輸出解析樹 XML（第九章）。

第十章會在同一個骨架上加入 CodeWriter，讓每個 compile* 方法
同時輸出 VM 程式碼。
"""

from __future__ import annotations

from typing import TextIO

from jack_error import JackError
from jack_tokenizer import Token, TokenType, JackTokenizer, token_to_xml

STATEMENT_KEYWORDS = {"let", "if", "while", "do", "return"}
OP_SYMBOLS = {"+", "-", "*", "/", "&", "|", "<", ">", "="}
UNARY_OPS = {"-", "~"}


class CompilationEngine:
    """依 Jack 文法剖析整個類別，輸出成對的 XML 標籤。"""

    def __init__(self, tokenizer: JackTokenizer, output: TextIO) -> None:
        self.t = tokenizer
        self.out = output
        self.indent = 0

    # ------------------------------------------------------------ 輸出 Helper

    def _write(self, text: str) -> None:
        self.out.write("  " * self.indent + text + "\n")

    def _open(self, tag: str) -> None:
        self._write(f"<{tag}>")
        self.indent += 1

    def _close(self, tag: str) -> None:
        self.indent -= 1
        self._write(f"</{tag}>")

    def _leaf(self, token: Token) -> None:
        self._write(token_to_xml(token))

    # ------------------------------------------------------------ 讀取 Helper

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

    # ------------------------------------------------------------ 頂層文法

    def compile_class(self) -> None:
        self._open("class")
        self._leaf(self._expect_keyword("class"))
        self._leaf(self._expect_identifier())
        self._leaf(self._expect_symbol("{"))

        while self._value() in ("static", "field"):
            self.compile_class_var_dec()
        while self._value() in ("constructor", "function", "method"):
            self.compile_subroutine()

        self._leaf(self._expect_symbol("}"))
        self._close("class")

        extra = self.t.peek()
        if extra is not None:
            raise self._error("類別結束後還有剩餘的 token", extra)

    def compile_class_var_dec(self) -> None:
        self._open("classVarDec")
        token = self.t.peek()
        if (
            token is None
            or token.type is not TokenType.KEYWORD
            or token.value not in ("static", "field")
        ):
            raise self._error("預期 static 或 field")
        self._leaf(self.t.advance())
        self.compile_type()
        self._leaf(self._expect_identifier())
        while self._value() == ",":
            self._leaf(self._expect_symbol(","))
            self._leaf(self._expect_identifier())
        self._leaf(self._expect_symbol(";"))
        self._close("classVarDec")

    def compile_subroutine(self) -> None:
        self._open("subroutineDec")
        token = self.t.peek()
        if (
            token is None
            or token.type is not TokenType.KEYWORD
            or token.value not in ("constructor", "function", "method")
        ):
            raise self._error("預期 constructor、function 或 method")
        self._leaf(self.t.advance())

        token = self.t.peek()
        if token and token.type is TokenType.KEYWORD and token.value == "void":
            self._leaf(self.t.advance())
        else:
            self.compile_type()

        self._leaf(self._expect_identifier())
        self._leaf(self._expect_symbol("("))
        self.compile_parameter_list()
        self._leaf(self._expect_symbol(")"))
        self.compile_subroutine_body()
        self._close("subroutineDec")

    def compile_type(self) -> None:
        token = self.t.peek()
        if token is None:
            raise self._error("預期資料型別")
        if (
            token.type is TokenType.KEYWORD
            and token.value in ("int", "char", "boolean")
        ) or token.type is TokenType.IDENTIFIER:
            self._leaf(self.t.advance())
            return
        raise self._error("預期 int、char、boolean 或類別名稱", token)

    def compile_parameter_list(self) -> None:
        self._open("parameterList")
        if self._value() != ")":
            self.compile_type()
            self._leaf(self._expect_identifier())
            while self._value() == ",":
                self._leaf(self._expect_symbol(","))
                self.compile_type()
                self._leaf(self._expect_identifier())
        self._close("parameterList")

    def compile_subroutine_body(self) -> None:
        self._open("subroutineBody")
        self._leaf(self._expect_symbol("{"))
        while self._value() == "var":
            self.compile_var_dec()
        self.compile_statements()
        self._leaf(self._expect_symbol("}"))
        self._close("subroutineBody")

    def compile_var_dec(self) -> None:
        self._open("varDec")
        self._leaf(self._expect_keyword("var"))
        self.compile_type()
        self._leaf(self._expect_identifier())
        while self._value() == ",":
            self._leaf(self._expect_symbol(","))
            self._leaf(self._expect_identifier())
        self._leaf(self._expect_symbol(";"))
        self._close("varDec")

    # ------------------------------------------------------------ 陳述式

    def compile_statements(self) -> None:
        self._open("statements")
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
        self._close("statements")

    def compile_let(self) -> None:
        self._open("letStatement")
        self._leaf(self._expect_keyword("let"))
        self._leaf(self._expect_identifier())
        if self._value() == "[":
            self._leaf(self._expect_symbol("["))
            self.compile_expression()
            self._leaf(self._expect_symbol("]"))
        self._leaf(self._expect_symbol("="))
        self.compile_expression()
        self._leaf(self._expect_symbol(";"))
        self._close("letStatement")

    def compile_if(self) -> None:
        self._open("ifStatement")
        self._leaf(self._expect_keyword("if"))
        self._leaf(self._expect_symbol("("))
        self.compile_expression()
        self._leaf(self._expect_symbol(")"))
        self._leaf(self._expect_symbol("{"))
        self.compile_statements()
        self._leaf(self._expect_symbol("}"))
        if self._value() == "else":
            self._leaf(self._expect_keyword("else"))
            self._leaf(self._expect_symbol("{"))
            self.compile_statements()
            self._leaf(self._expect_symbol("}"))
        self._close("ifStatement")

    def compile_while(self) -> None:
        self._open("whileStatement")
        self._leaf(self._expect_keyword("while"))
        self._leaf(self._expect_symbol("("))
        self.compile_expression()
        self._leaf(self._expect_symbol(")"))
        self._leaf(self._expect_symbol("{"))
        self.compile_statements()
        self._leaf(self._expect_symbol("}"))
        self._close("whileStatement")

    def compile_do(self) -> None:
        self._open("doStatement")
        self._leaf(self._expect_keyword("do"))
        self._compile_subroutine_call()
        self._leaf(self._expect_symbol(";"))
        self._close("doStatement")

    def compile_return(self) -> None:
        self._open("returnStatement")
        self._leaf(self._expect_keyword("return"))
        if self._value() != ";":
            self.compile_expression()
        self._leaf(self._expect_symbol(";"))
        self._close("returnStatement")

    def _compile_subroutine_call(self) -> None:
        self._leaf(self._expect_identifier())
        if self._value() == ".":
            self._leaf(self._expect_symbol("."))
            self._leaf(self._expect_identifier())
        self._leaf(self._expect_symbol("("))
        self.compile_expression_list()
        self._leaf(self._expect_symbol(")"))

    # ------------------------------------------------------------ 運算式

    def compile_expression(self) -> None:
        self._open("expression")
        self.compile_term()
        while self._value() in OP_SYMBOLS:
            self._leaf(self.t.advance())
            self.compile_term()
        self._close("expression")

    def compile_term(self) -> None:
        self._open("term")
        token = self.t.peek()
        if token is None:
            raise self._error("預期 term，但已到檔案結尾")

        if token.type in (TokenType.INT_CONST, TokenType.STRING_CONST):
            self._leaf(self.t.advance())
        elif token.type is TokenType.KEYWORD and token.value in (
            "true", "false", "null", "this"
        ):
            self._leaf(self.t.advance())
        elif token.type is TokenType.SYMBOL and token.value == "(":
            self._leaf(self.t.advance())
            self.compile_expression()
            self._leaf(self._expect_symbol(")"))
        elif token.type is TokenType.SYMBOL and token.value in UNARY_OPS:
            self._leaf(self.t.advance())
            self.compile_term()
        elif token.type is TokenType.IDENTIFIER:
            self._leaf(self.t.advance())
            following = self._value()
            if following == "[":
                self._leaf(self._expect_symbol("["))
                self.compile_expression()
                self._leaf(self._expect_symbol("]"))
            elif following == "(":
                self._leaf(self._expect_symbol("("))
                self.compile_expression_list()
                self._leaf(self._expect_symbol(")"))
            elif following == ".":
                self._leaf(self._expect_symbol("."))
                self._leaf(self._expect_identifier())
                self._leaf(self._expect_symbol("("))
                self.compile_expression_list()
                self._leaf(self._expect_symbol(")"))
        else:
            raise self._error("無法辨識的 term", token)
        self._close("term")

    def compile_expression_list(self) -> None:
        self._open("expressionList")
        if self._value() != ")":
            self.compile_expression()
            while self._value() == ",":
                self._leaf(self._expect_symbol(","))
                self.compile_expression()
        self._close("expressionList")
