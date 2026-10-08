// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/04/Mult.asm

// Multiplies R0 and R1 and stores the result in R2.
// (R0, R1, R2 refer to RAM[0], RAM[1], and RAM[2], respectively.)

// Put your code here.
// Mult.asm: R2 = R0 * R1
// R0, R1, R2 對應 RAM[0], RAM[1], RAM[2]

// 1. 初始化 R2 = 0
    @R2
    M=0

// 2. 將 R1 的值載入到變數 i (作為計數器)
    @R1
    D=M
    @i
    M=D

(LOOP)
// 3. 檢查條件：若 i <= 0，則跳轉至 END
    @i
    D=M
    @END
    D;JLE   // If i <= 0 jump to END

// 4. 執行累加：R2 = R2 + R0
    @R0
    D=M
    @R2
    M=M+D   // R2 = R2 + R0

// 5. 計數器遞減：i = i - 1
    @i
    M=M-1   // i = i - 1

// 6. 跳回 LOOP 繼續下一輪
    @LOOP
    0;JMP

(END)
// 7. 無窮迴圈 (防止 CPU 繼續往下跑)
    @END
    0;JMP