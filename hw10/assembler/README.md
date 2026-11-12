# Hack 組譯器（Nand2Tetris Project 6）

把 Hack 組合語言 `.asm` 翻譯成 Hack 機器碼 `.hack`。
每個指令固定 16 bits，輸出檔每行就是 16 個 `0`/`1`。純 Python 標準庫，不需要 `pip install`。

---

## 一、簡短介紹

Nand2Tetris（The Elements of Computing Systems）Part I 的 Project 6，要寫一個「組譯器」（assembler）：
把人類看得懂的 Hack 組合語言，翻成我們自己做的 CPU 吃得懂的 0/1 機器碼。

```
   Add.asm                        Assembler                       Add.hack
┌──────────────┐              ┌──────────────┐              ┌──────────────────┐
│ @2           │              │  Pass 1      │              │ 0000000000000010 │
│ D=A          │  ─────────►  │  建標籤表     │  ─────────►  │ 1110110000010000 │
│ @3           │              │  Pass 2      │              │ 0000000000000011 │
│ D=D+A        │              │  產生機器碼   │              │ 1110000010010000 │
└──────────────┘              └──────────────┘              └──────────────────┘
```

重點在「**兩階段符號解析**」：`@LOOP` 可能寫在 `(LOOP)` 之前，所以不能只掃一遍。

### 檔案結構

```
assembler/
├── assembler.py     # 主程式：兩階段流程、命令列介面
├── hack_code.py     # dest / comp / jump 三張對照表
├── symbol_table.py  # 預定義符號 + 標籤/變數表
├── README.md
└── tests/
    ├── run_tests.py
    ├── Add.asm             Add.expected.hack
    ├── Symbols.asm         Symbols.expected.hack
    ├── Rect.asm            Rect.expected.hack
    └── invalid/Bad_comp.asm   # 故意寫錯，用來驗證錯誤訊息
```

> 模組命名為 `hack_code` 而不是 `code`，是為了不蓋掉 Python 標準庫的 `code` 模組（除錯工具 `pdb` 會用到）。

---

## 二、使用方式

### 環境需求

- Python 3.9 以上（開發時以 3.13 驗證；只用標準庫）
- Windows / macOS / Linux 皆可

### 快速開始

```bash
# 單一檔案：輸出同名的 .hack
python assembler.py tests/Add.asm

# 指定輸出路徑
python assembler.py tests/Add.asm out/Add.hack

# 一次組譯資料夾內所有 .asm
python assembler.py tests

# 顯示統計資訊（指令數、標籤數、變數名稱）
python assembler.py tests/Add.asm -v
```

### 執行輸出

```
[完成] tests\Add.asm → tests\Add.hack（6 個指令）
```

加上 `-v`：

```
來源      ：tests\Add.asm
輸出      ：tests\Add.hack
指令數    ：6
標籤數    ：0
變數數    ：0
符號總數  ：0（不含預定義符號）
```

### 測試

```bash
python tests/run_tests.py
```

會依序組譯 `tests/*.asm`，與 `*.expected.hack` 逐行比對，並印出通過／失敗統計：

```
[通過] Add.asm（6 個指令）
[通過] Rect.asm（21 個指令）
[通過] Symbols.asm（14 個指令）

結果：3 通過、0 失敗
```

### 錯誤訊息範例

```bash
python assembler.py tests/invalid/Bad_comp.asm
# [失敗] tests\invalid\Bad_comp.asm：第 3 行「D=D+Q」：未知的 comp「D+Q」，合法值：...
```

程式碼會自動處理：`//` 註解（含行內）、所有空白與 Tab、CRLF、UTF-8（含 BOM）與 Big5/cp950 編碼的來源檔。

---

## 三、詳細說明

### 3.1 組譯器在做什麼

Project 6 要把 **Hack 組合語言（`.asm`）** 翻譯成 **Hack 機器碼（`.hack`）**。

Hack 是 16 位元平台，每個指令固定 16 bits，所以輸出檔就是每行 16 個 `0`/`1`：

```
0000000000000010
1110110000010000
...
```

組譯器本身執行在「宿主電腦」上（用 Python、Java、C++ 寫都行），跟 Hack 硬體無關；它的產物才是給 CPU Emulator、或自己做的那顆 CPU 吃的。

### 3.2 輸入語言的元素

| 元素 | 寫法 | 產出 |
|---|---|---|
| A 指令 | `@value` | 16 bits，最高位 `0` |
| C 指令 | `dest=comp;jump` | 16 bits，最高位 `1` |
| 標籤宣告 | `(LOOP)` | **不產生機器碼**，只記位址 |
| 變數 | 未定義的符號 | 自動配到 RAM 16 以後 |
| 註解／空白 | `// ...`、空行 | 全部忽略 |

**A 指令**：`0` + 15 bits 位址。`value` 可以是十進位常數（0–32767），也可以是符號。

**C 指令**的 16 bits 配置：

```
1 1 1 a c1 c2 c3 c4 c5 c6 d1 d2 d3 j1 j2 j3
└─┬─┘ └──── comp ────┘ └ dest ┘ └ jump ┘
固定 111
```

- `comp` 佔 7 bits（`a` + `c1..c6`），`a=1` 表示運算用到 `M`（記憶體），`a=0` 表示只用 `A`／`D`。
- `dest` 佔 3 bits，只能是 `A`、`M`、`D` 的組合（含空，代表不存）。
- `jump` 佔 3 bits。

**dest 對照表**

| dest | d1 d2 d3 |
|---|---|
| 空 | 000 |
| M | 001 |
| D | 010 |
| MD | 011 |
| A | 100 |
| AM | 101 |
| AD | 110 |
| AMD | 111 |

**jump 對照表**

| jump | j1 j2 j3 | 條件 |
|---|---|---|
| 空 | 000 | 不跳 |
| JGT | 001 | > 0 |
| JEQ | 010 | = 0 |
| JGE | 011 | ≥ 0 |
| JLT | 100 | < 0 |
| JNE | 101 | ≠ 0 |
| JLE | 110 | ≤ 0 |
| JMP | 111 | 無條件 |

**comp 對照表**（`hack_code.py` 內容，共 28 個合法組合）

| comp | 7 bits | comp | 7 bits |
|---|---|---|---|
| `0` | 0101010 | `D+1` | 0011111 |
| `1` | 0111111 | `A+1` | 0110111 |
| `-1` | 0111010 | `M+1` | 1110111 |
| `D` | 0001100 | `D-1` | 0001110 |
| `A` | 0110000 | `A-1` | 0110010 |
| `M` | 1110000 | `M-1` | 1110010 |
| `!D` | 0001101 | `D+A` | 0000010 |
| `!A` | 0110001 | `D+M` | 1000010 |
| `!M` | 1110001 | `D-A` | 0010011 |
| `-D` | 0001111 | `D-M` | 1010011 |
| `-A` | 0110011 | `A-D` | 0000111 |
| `-M` | 1110011 | `M-D` | 1000111 |
| `D&A` | 0000000 | `D\|A` | 0010101 |
| `D&M` | 1000000 | `D\|M` | 1010101 |

### 3.3 預定義符號

| 符號 | 位址 |
|---|---|
| `R0`–`R15` | 0–15 |
| `SP` / `LCL` / `ARG` / `THIS` / `THAT` | 0 / 1 / 2 / 3 / 4 |
| `SCREEN` | 16384 |
| `KBD` | 24576 |

這也是為什麼**使用者變數從 16 開始配**：0–15 已經被 R0–R15 佔走了。

### 3.4 核心演算法：兩階段（two-pass）

不能只掃一遍，因為 `@LOOP` 可能寫在 `(LOOP)` **之前**（向前引用），掃到 `@LOOP` 時還不知道位址。

```
原始碼
  │
  ├─ Pass 1 ─► 符號表（只有標籤 → ROM 位址）
  │
  └─ Pass 2 ─► 機器碼（變數在這裡才配置 RAM 位址）
```

**Pass 1：只建符號表，不產生機器碼**

1. 逐行讀入，去掉註解與空白，跳過空行。
2. 遇到 `(XXX)`：把 `XXX → 目前指令的 ROM 位址`（也就是已經數過的 A/C 指令數量，從 0 起算）寫進符號表。標籤本身不佔位址。
3. 其他行都是 A 或 C 指令 → 指令計數 +1。
4. 順便讓符號表先載入預定義符號。

**Pass 2：真正產生機器碼**

1. 再掃一遍（標籤行直接跳過）。
2. A 指令：`@` 後面若是數字 → 直接轉 15 bits；若是符號 → 查表；查不到就**新增為變數**，配一個 `next_ram`（初始 16）並遞增。
3. C 指令：把 `dest`、`comp`、`jump` 三段分別查對照表，前面補 `111` 組成 16 bits。
4. 每行輸出成 16 個字元的 `0`/`1`。

> 重點：**標籤在 Pass 1 定址，變數在 Pass 2 才配置**。兩者處理時機不同，這是初學者最常搞混的地方。

### 3.5 本專案的模組對應（書上的骨架）

| 書上模組 | 本專案檔案 | 職責 |
|---|---|---|
| `Parser` | `assembler.py`（`clean` / `parse_label` / `encode_c_instruction`） | 拆行、去註解空白、判斷指令型別、取出符號／`dest`／`comp`／`jump` |
| `Code` | `hack_code.py` | 三張對照表：`dest_bits()`、`comp_bits()`、`jump_bits()` |
| `SymbolTable` | `symbol_table.py` | `add_entry`、`contains`、`get_address` |
| `HackAssembler` | `assembler.py`（`assemble_file` / `main`） | 跑 Pass 1、Pass 2、寫檔、命令列介面 |

`comp` 對照表建議直接抄書上的表，不要自己用位元運算推，容易錯。

### 3.6 完整範例

`tests/Add.asm`：

```
@2
D=A
@3
D=D+A
@0
M=D
```

翻譯結果：

| 原始碼 | 機器碼 | 說明 |
|---|---|---|
| `@2` | `0000000000000010` | 常數 2 |
| `D=A` | `1110110000010000` | comp=`A`(0110000)，dest=`D`(010) |
| `@3` | `0000000000000011` | 常數 3 |
| `D=D+A` | `1110000010010000` | comp=`D+A`(0000010)，dest=`D`(010) |
| `@0` | `0000000000000000` | 常數 0 |
| `M=D` | `1110001100001000` | comp=`D`(0001100)，dest=`M`(001) |

再看標籤與變數（`tests/Symbols.asm` 節錄）：

```
@counter        // counter 是新符號 → 配 RAM[16]
M=1
(LOOP)          // LOOP → ROM 2（標籤不佔位址）
    ...
@LOOP           // 查表得到 2
0;JMP
```

### 3.7 錯誤訊息與限制

程式碼中的檢查：

| 情況 | 訊息 |
|---|---|
| 常數或位址 > 32767 | `常數 40000 超出範圍（0~32767）` |
| ROM 超過 32768 個指令 | `程式超過 ROM 容量（最多 32768 個指令）` |
| 標籤重複 | `標籤「LOOP」重複定義` |
| 未知的 comp／dest／jump | `未知的 comp「D+Q」，合法值：...` |
| 缺 dest／comp／jump | `「=」左邊缺少 dest`、`缺少 comp 運算` |
| 符號含非法字元 | `符號「a-b」含有非法字元「-」` |

其他限制：

- 符號區分大小寫（`R0` ≠ `r0`），可用字元為英文字母、數字、`_ . $ :`，且不能以數字開頭。
- 一行只能有一個指令。
- `.hack` 每行必須剛好 16 個字元。

### 3.8 常見錯誤檢查清單

- 標籤被算進指令位址（錯：`(LOOP)` 之後的位址沒對齊）。
- 變數起始位址寫成 0 而不是 16。
- 行內註解沒清掉（`D=A // 註解` 直接餵給對照表 → 查不到）。
- `comp` 含 `M` 時忘了把 `a` 設成 1。
- `dest` 或 `jump` 省略時沒給 `000`。
- `@` 的常數超過 32767，或符號位址超過 32767。
- 大小寫混用（`r0` 不是 `R0`）。

### 3.9 如何驗證

1. 跑 `python tests/run_tests.py`：與手工計算的預期答案逐行比對。
2. 拿官方 `Tools/Assembler.bat` 產一份標準答案，逐行比較：

   ```powershell
   fc.exe /n tests\Pong.hack official\Pong.hack
   ```

3. 丟進 `CPUEmulator` 執行，看記憶體／螢幕結果是否正確。
4. 由簡到繁跑官方測試檔（`Add`、`Max`、`Rect`、`Pong`），`Pong.asm` 用大量變數與標籤，通過了基本就沒問題。
