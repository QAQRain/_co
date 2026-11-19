# VM 翻譯器（Nand2Tetris Project 7 + 8）

把 `.vm` 虛擬機程式翻譯成 Hack 組合語言 `.asm`，再交給專案內 Project 6 的 `assembler.py` 組譯成 `.hack`。純 Python 標準庫，不需要 `pip install`。

---

## 一、簡介

Nand2Tetris（The Elements of Computing Systems）Part I 的第 7、8 章要寫一個 VM 翻譯器：

- **第 7 章（Stack Arithmetic）**：處理堆疊算術（`add`、`sub`、`neg`、`and`、`or`、`eq`、`gt`、`lt`）與 `push`／`pop` 八個記憶體區段。
- **第 8 章（Program Control）**：處理 `label`、`goto`、`if-goto`，以及 `function`、`call`、`return` 與程式啟動程序（bootstrap）。

```
   SimpleAdd.vm              VM Translator              SimpleAdd.asm
┌────────────────┐         ┌────────────────┐         ┌────────────────┐
│ push constant 7│         │ Parser         │         │ @7             │
│ push constant 8│ ──────► │ CodeWriter     │ ──────► │ D=A            │
│ add            │         │                │         │ ...            │
└────────────────┘         └────────────────┘         └────────────────┘
```

---

## 二、系統需求

- Python 3.9 以上（只用標準庫）
- Windows / macOS / Linux 皆可
- 不需要網路

## 三、安裝方式

不需要安裝。直接在 `school/for_co/vm/` 目錄執行即可。

## 四、使用方式

### 單檔翻譯（第 7 章測試適用）

```powershell
python vm_translator.py tests/ch7/SimpleAdd.vm
python vm_translator.py tests/ch7/SimpleAdd.vm out.asm
python vm_translator.py tests/ch7/SimpleAdd.vm -v
```

預設輸出成同名的 `.asm`。單檔模式**不會**加入啟動程序。

### 資料夾合併翻譯（第 8 章多檔測試適用）

```powershell
python vm_translator.py tests/ch8/multi
python vm_translator.py tests/ch8/multi --no-bootstrap
```

資料夾模式會把該層所有 `.vm` 合併成一個 `.asm`（例如 `tests/ch8/multi.asm`）。若資料夾內含 `Sys.vm`，會自動加入啟動程序；可用 `--bootstrap`／`--no-bootstrap` 覆蓋判斷。

> 第 7 章的獨立測試請用單檔模式，不要放在同一層用資料夾模式，否則會被錯誤合併。

### 串接組譯器

```powershell
python vm_translator.py tests/ch7/SimpleAdd.vm
python ../assembler/assembler.py tests/ch7/SimpleAdd.asm -v
```

### 煙霧測試

```powershell
python tests/run_tests.py
```

會把 `tests/` 底下所有 `.vm` 分別用單檔模式與資料夾合併模式翻譯，再交給 `assembler.py` 組譯，並檢查每行都是 16 位元機器碼。

### 關閉方式

這是命令列程式，執行完畢即自動結束。沒有開啟伺服器、背景程式或常駐服務，不需要額外關閉。

---

## 五、檔案結構

```
vm/
├── vm_translator.py     # CLI 進入點：單檔／資料夾模式、啟動程序判斷
├── vm_parser.py         # 去註解、拆解指令、驗證參數
├── code_writer.py       # 產生 Hack 組語
├── vm_error.py          # 帶檔名與行號的錯誤訊息
├── README.md
└── tests/
    ├── run_tests.py     # 翻譯 + 組譯的煙霧測試
    ├── ch7/             # 第 7 章自製案例
    │   ├── SimpleAdd.vm
    │   └── StackTest.vm
    └── ch8/             # 第 8 章自製案例
        ├── SimpleFunction.vm
        ├── NestedCall.vm
        └── multi/       # 多檔合併 + 啟動程序案例
            ├── Sys.vm
            └── Class1.vm
```

專案內對應的上一層目錄：

```
school/for_co/
├── assembler/           # Project 6 的組譯器
└── vm/                  # 本專案
```

---

## 六、功能說明

- 算術與邏輯：`add`、`sub`、`neg`、`and`、`or`、`eq`、`gt`、`lt`
- 記憶體區段：`constant`、`local`、`argument`、`this`、`that`、`temp`、`pointer`、`static`
- 流程控制：`label`、`goto`、`if-goto`
- 函式：`function`、`call`、`return`
- 啟動程序：`SP = 256` 並呼叫 `Sys.init 0`
- 單檔與資料夾合併翻譯、詳細統計（`--verbose`）、帶行號的錯誤訊息

---

## 七、資料來源與授權

- 規格來源：Nand2Tetris（The Elements of Computing Systems）教材第 7、8 章。
- 本目錄的程式碼與測試案例為自行撰寫，未使用外部資料或圖片。
- 不使用第三方套件。

---

## 八、已知限制

- 刻意不模仿官方翻譯器的暫存器與標籤命名，因此產生的 `.asm` **無法**與官方 `.expected.asm` 逐行比對；請用官方 CPUEmulator／VMEmulator 驗證語意。
- 資料夾模式只處理該層的 `.vm`，不遞迴搜索子資料夾。
- 不檢查堆疊溢位或 RAM 容量上限。
- `static` 以檔名為前綴，因此多檔合併時每個 `.vm` 的 `static 0` 是不同變數。
