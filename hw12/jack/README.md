# Jack 編譯器（Nand2Tetris Project 9–11）

把 Jack 語言 `.jack` 轉成 XML（第九章）、VM 程式 `.vm`（第十章），並用 Jack 實作的作業系統把它們真正跑起來（第十一章）。純 Python 標準庫，不需要 `pip install`。

各章檔案彼此獨立：第九章的 `jack_analyzer.py` 保持原樣，第十章另外新增 `jack_compiler.py`，第十一章 OS 放在 `tests/11/OS/`。

```text
第九章   .jack → Tokenizer → Parser     → .xml（驗證語法結構）
第十章   .jack → Compiler               → .vm
第七、八章                   .vm → .asm
第六章                       .asm → .hack
第十一章 OS（八個 Jack 類別）↑ 補齊被呼叫的標準函式庫
CPU Emulator                      跑 .tst / .cmp 驗證結果
```

### 設計理念

本專案刻意分章實作，而不是一次寫出完整的 Jack 編譯器。教材與課堂允許直接產生完整編譯器，但那樣會省略第九章的 XML 剖析與第十章的 VM 輸出這兩個中間產物，看不到語法分析如何一步步變成機器碼。

保留中間層之後，開發與驗證就能分段進行：先用官方 XML 逐行比對確認剖析正確，再於同一套文法骨架上加入 VM 輸出，最後補上以 Jack 寫成的作業系統，讓程式真的在 CPU Emulator 上執行。每一章的輸出都是下一章的輸入，因此能清楚定位問題出在哪一層。

---

## 一、系統需求

- Python 3.9 以上（只用標準庫）
- Windows / macOS / Linux 皆可
- 不需要網路

## 二、安裝方式

不需要安裝。直接在專案根目錄或 `school/for_co/jack` 目錄執行即可。

## 三、使用方式

### 第九章：轉成 XML

```powershell
python school/for_co/jack/jack_analyzer.py Main.jack
python school/for_co/jack/jack_analyzer.py Main.jack -t
python school/for_co/jack/jack_analyzer.py school/for_co/jack/tests/09/Square
```

### 第十章：轉成 VM

```powershell
python school/for_co/jack/jack_compiler.py school/for_co/jack/tests/09/Square/Square.jack -v
python school/for_co/jack/jack_compiler.py school/for_co/jack/tests/09/Square
```

### 第十一章：作業系統

八個 OS 類別寫成 Jack，放在 `tests/11/OS/`。先編譯 OS：

```powershell
cd school/for_co/jack
python jack_compiler.py tests/11/OS -v
```

再執行一鍵建置（OS 與每個測試程式合併翻譯、組譯）：

```powershell
python tests/run_tests_ch11.py
```

每個測試資料夾會產生 `_build/`（內含全部 `.vm`）、`_build.asm`、`_build.hack`。用 CPU Emulator 載入 `_build.hack` 或對應的 `.tst`，即可看到螢幕輸出。

> 第十一章的 `_build` 資料夾含 `Sys.vm`，VM 翻譯器會自動插入 bootstrap，**不要**加 `--no-bootstrap`。

### 測試

```powershell
# 第九章：與官方 XML 逐行比對
python school/for_co/jack/tests/run_tests.py

# 第十章：.jack → .vm → .asm → .hack 全流程煙霧測試
python school/for_co/jack/tests/run_tests_ch10.py

# 第十一章：OS + 測試程式建置
python school/for_co/jack/tests/run_tests_ch11.py
```

### 關閉方式

命令列程式，執行完畢即自動結束，沒有伺服器或常駐服務，不需要額外關閉。

---

## 四、檔案結構

```text
jack/
├── jack_analyzer.py        # 第九章 CLI：輸出 token XML 與解析樹 XML
├── jack_tokenizer.py       # 去註解、切 token、XML 轉義（共用）
├── compilation_engine.py   # 第九章剖析器，輸出解析樹 XML
├── jack_compiler.py        # 第十章 CLI 與剖析器，輸出 .vm
├── jack_symbol_table.py    # 第十章符號表（避免與 assembler 同名衝突）
├── vm_writer.py            # 第十章 VM 指令輸出後端
├── jack_error.py           # 帶檔名與行號的錯誤訊息
├── README.md
└── tests/
    ├── run_tests.py        # 第九章測試
    ├── run_tests_ch10.py   # 第十章測試
    ├── run_tests_ch11.py   # 第十一章建置測試
    ├── Simple/             # 自製案例
    ├── 09/                 # 官方第九章案例
    ├── 10/                 # 官方第十章案例
    └── 11/
        ├── OS/             # 八個 Jack OS 類別
        ├── Average/
        ├── ComplexArrays/
        ├── ConvertToBin/
        ├── Pong/
        ├── Seven/
        └── Square/
```

---

## 五、功能說明

### 第九章

- 去除 `//` 與 `/* ... */` 註解
- 五類 token：keyword、symbol、identifier、integerConstant、stringConstant
- XML 特殊字元轉義
- 完整 Jack 文法解析樹，固定兩空格縮排

### 第十章

- 兩層符號表：`static` / `field` 屬於類別，`arg` / `var` 屬於副程式
- `constructor` 自動插入 `Memory.alloc`，`method` 自動把 `this` 設為 `argument 0`
- 變數與陣列存取、`if` / `else` / `while` 跳轉、`do` 呼叫後丟棄回傳值
- 所有運算子、常數、字串建立（`String.new` + `String.appendChar`）

### 第十一章 OS

| 類別 | 負責什麼 |
|---|---|
| `Math` | 加減乘除（含負數）、平方根、絕對值、最大最小 |
| `String` | 字串建立、附加、字元存取、整數轉換 |
| `Array` | 陣列配置與釋放 |
| `Output` | 遊標、印字、印整數、換行 |
| `Screen` | 畫點、畫線、畫矩形、圓、清螢幕 |
| `Keyboard` | 讀取按鍵、讀字元、讀整行、讀整數 |
| `Memory` | heap 配置、RAM 直接 peek／poke |
| `Sys` | 系統啟動、halt、error、wait |

`Memory.peek` / `poke` 的技巧是把整數位址當成 `Array` 基底，再用 `ram[0]` 讀寫 RAM。

---

## 六、資料來源與授權

- 規格來源：Nand2Tetris（The Elements of Computing Systems）第九～十一章。
- 本目錄的程式碼與測試案例為自行撰寫，未使用外部資料或圖片。
- 官方第九章、第十章案例與第十一章測試程式由使用者自行放入 `tests/`。
- 不使用第三方套件。

---

## 七、已知限制

- 第九章解析樹的縮排固定為兩空格，與官方 XML 逐行比對時必須完全一致。
- 第十章目前只有煙霧測試（確認能轉成合法的 16 位元機器碼），尚未與官方第十章預期 `.vm` 逐行比對。
- 第十一章的 OS 是精簡實作：
  - `Memory.deAlloc` 不回收記憶體，heap 只增不減；長時間執行的程式可能耗盡 heap。
  - `Output.printChar` 把所有字元畫成 5×7 方塊，不是真正的字型；文字辨識度有限，但不影響圖形輸出。
  - `Screen.drawCircle` 只畫水平與垂直直徑。
  - `Sys.wait` 用固定迴圈計時，非精確時間。
- `ComplexArrays` 產生接近 30000 個機器碼，接近 Hack ROM 的 32768 上限；更大的程式可能超標。
- 要在 CPU Emulator 真正執行，仍需官方 `.tst`／`.cmp` 做最終驗證；目前第十一章只確認能產生合法 `.hack`。
