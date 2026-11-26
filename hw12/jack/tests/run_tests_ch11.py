#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第十一章建置測試：把八個 OS 與每個測試程式一起編譯成 .hack。

流程：
    .jack（OS + 測試） → .vm → 含 Sys.vm 的資料夾 → .asm（自動 bootstrap） → .hack

每個測試資料夾會產生 _build/、_build.asm、_build.hack，不覆蓋官方檔。
"""

from __future__ import annotations

import shutil
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

CH11 = HERE / "11"
OS_DIR = CH11 / "OS"


def check_hack(path: Path) -> int:
    lines = path.read_text(encoding="ascii").splitlines()
    if not lines:
        raise AssertionError("沒有產生機器碼")
    for index, line in enumerate(lines, start=1):
        if len(line) != 16 or set(line) - {"0", "1"}:
            raise AssertionError(f"第 {index} 行不是 16 位元：{line}")
    return len(lines)


def ensure_os_vms() -> list[Path]:
    OS_FILES = sorted(OS_DIR.glob("*.jack"))
    if len(OS_FILES) != 8:
        raise AssertionError(f"OS 資料夾應有 8 個 .jack，實際找到 {len(OS_FILES)} 個")
    result: list[Path] = []
    for jack in OS_FILES:
        vm = jack.with_suffix(".vm")
        if not vm.exists():
            jack_compiler.compile_file(jack)
        result.append(vm)
    return result


def build_case(case_dir: Path, os_vms: list[Path]) -> dict:
    build_dir = case_dir / "_build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir()

    for vm in os_vms:
        shutil.copy2(vm, build_dir / vm.name)

    jack_files = sorted(case_dir.glob("*.jack"))
    if not jack_files:
        raise AssertionError("資料夾裡沒有 .jack")
    for jack in jack_files:
        jack_compiler.compile_file(jack)
        vm = jack.with_suffix(".vm")
        shutil.copy2(vm, build_dir / vm.name)

    asm_stats = vm_translator.translate_source(build_dir)
    hack_stats = assembler.assemble_file(asm_stats["output"])
    machine_count = check_hack(hack_stats["output"])

    return {
        "vm_files": len(list(build_dir.glob("*.vm"))),
        "asm_lines": asm_stats["asm_lines"],
        "machine_count": machine_count,
        "hack": hack_stats["output"],
    }


def main() -> int:
    if not CH11.is_dir():
        print(f"錯誤：找不到 {CH11}")
        return 2
    try:
        os_vms = ensure_os_vms()
    except Exception as exc:
        print(f"[失敗] OS：{exc}")
        return 2

    cases = sorted(
        path
        for path in CH11.iterdir()
        if path.is_dir() and path.name != "OS" and list(path.glob("*.jack"))
    )
    if not cases:
        print("找不到測試資料夾")
        return 2

    passed = 0
    failed = 0
    for case in cases:
        try:
            stats = build_case(case, os_vms)
        except Exception as exc:
            print(f"[失敗] {case.name}：{exc}")
            failed += 1
            continue
        print(
            f"[通過] {case.name}（{stats['vm_files']} 個 .vm、"
            f"{stats['asm_lines']} 行 ASM → {stats['machine_count']} 個機器碼）"
        )
        passed += 1

    print(f"\n結果：{passed} 通過、{failed} 失敗")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
