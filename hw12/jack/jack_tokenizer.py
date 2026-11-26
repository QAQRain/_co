#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JackTokenizer：讀取 .jack、去掉註解、切成五類 token。

第九章只要輸出 token 的 XML 清單（MainT.xml），第十章才會把
這些 token 真正的翻譯成 VM 程式。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from jack_error import JackError

KEYWORDS = {
    "class", "constructor", "function", "method",
    "static", "field", "var", "int", "char", "boolean", "void",
    "true", "false", "null", "this",
    "let", "do", "if", "else", "while", "return",
}
SYMBOLS = set("{}()[].,;+-*/&|<>=~")
XML_ESCAPE = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
}
MAX_INT = 32767


class TokenType(Enum):
    KEYWORD = "keyword"
    SYMBOL = "symbol"
    IDENTIFIER = "identifier"
    INT_CONST = "integerConstant"
    STRING_CONST = "stringConstant"


@dataclass(frozen=True)
class Token:
    type: TokenType
    value: str
    lineno: int


def escape_xml(text: str) -> str:
    """把 XML 特殊字元轉成實體引用。"""
    return "".join(XML_ESCAPE.get(ch, ch) for ch in text)


def token_to_xml(token: Token) -> str:
    """一個 token 輸出成一行 XML。"""
    if token.type in (TokenType.SYMBOL, TokenType.STRING_CONST):
        value = escape_xml(token.value)
    else:
        value = token.value
    tag = token.type.value
    return f"<{tag}> {value} </{tag}>"


def read_source_lines(path: Path) -> list[str]:
    """先試 UTF-8（順便吃掉 BOM），再退回 cp950。"""
    if not path.is_file():
        raise FileNotFoundError(f"找不到檔案：{path}")
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = path.read_text(encoding="cp950", errors="replace")
    return text.splitlines()


def strip_comments(lines: list[str]) -> list[tuple[int, str]]:
    """去掉 // 與 /* ... */ 註解，保留行號。"""
    cleaned: list[tuple[int, str]] = []
    in_block = False
    for lineno, raw in enumerate(lines, start=1):
        out: list[str] = []
        index = 0
        while index < len(raw):
            if in_block:
                if raw.startswith("*/", index):
                    in_block = False
                    index += 2
                else:
                    index += 1
                continue
            if raw.startswith("//", index):
                break
            if raw.startswith("/*", index):
                in_block = True
                index += 2
                continue
            out.append(raw[index])
            index += 1
        cleaned.append((lineno, "".join(out)))
    return cleaned


def tokenize(path: str | Path) -> list[Token]:
    """把一個 .jack 檔切成 token 串列。"""
    source = Path(path)
    tokens: list[Token] = []

    for lineno, line in strip_comments(read_source_lines(source)):
        index = 0
        while index < len(line):
            char = line[index]

            if char.isspace():
                index += 1
                continue

            if char == '"':
                end = line.find('"', index + 1)
                if end == -1:
                    raise JackError(lineno, line, "字串常數缺少結尾引號", source)
                value = line[index + 1:end]
                tokens.append(Token(TokenType.STRING_CONST, value, lineno))
                index = end + 1
                continue

            if char in SYMBOLS:
                tokens.append(Token(TokenType.SYMBOL, char, lineno))
                index += 1
                continue

            if char.isascii() and (char.isalpha() or char == "_"):
                end = index + 1
                while end < len(line) and (
                    line[end].isascii() and (line[end].isalnum() or line[end] == "_")
                ):
                    end += 1
                word = line[index:end]
                kind = TokenType.KEYWORD if word in KEYWORDS else TokenType.IDENTIFIER
                tokens.append(Token(kind, word, lineno))
                index = end
                continue

            if char.isascii() and char.isdigit():
                end = index + 1
                while end < len(line) and line[end].isascii() and line[end].isdigit():
                    end += 1
                text = line[index:end]
                value = int(text)
                if value > MAX_INT:
                    raise JackError(
                        lineno, line, f"整數常數 {value} 超出範圍（0~{MAX_INT}）", source
                    )
                tokens.append(Token(TokenType.INT_CONST, str(value), lineno))
                index = end
                continue

            raise JackError(lineno, line, f"無法辨識的字元「{char}」", source)

    return tokens


class JackTokenizer:
    """提供教材風格的走訪介面，並附加 peek() 方便剖析器使用。"""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.tokens = tokenize(self.path)
        self._index = 0

    def __len__(self) -> int:
        return len(self.tokens)

    def has_more_tokens(self) -> bool:
        return self._index < len(self.tokens)

    def peek(self) -> Token | None:
        if not self.has_more_tokens():
            return None
        return self.tokens[self._index]

    def advance(self) -> Token:
        token = self.peek()
        if token is None:
            raise JackError(0, "檔案結尾", "沒有更多 token 可供讀取", self.path)
        self._index += 1
        return token

    def token_type(self) -> TokenType:
        token = self.peek()
        if token is None:
            raise JackError(0, "檔案結尾", "目前沒有 token", self.path)
        return token.type

    def keyword(self) -> str:
        return self._value_of(TokenType.KEYWORD)

    def symbol(self) -> str:
        return self._value_of(TokenType.SYMBOL)

    def identifier(self) -> str:
        return self._value_of(TokenType.IDENTIFIER)

    def int_val(self) -> int:
        return int(self._value_of(TokenType.INT_CONST))

    def string_val(self) -> str:
        return self._value_of(TokenType.STRING_CONST)

    def _value_of(self, kind: TokenType) -> str:
        token = self.peek()
        if token is None or token.type is not kind:
            raise JackError(
                token.lineno if token else 0,
                token.value if token else "檔案結尾",
                f"目前的 token 不是 {kind.value}",
                self.path,
            )
        return token.value
