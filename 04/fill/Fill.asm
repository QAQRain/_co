// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/04/Fill.asm

// Runs an infinite loop that listens to the keyboard input.
// When a key is pressed (any key), the program blackens the screen,
// i.e. writes "black" in every pixel;
// the screen should remain fully black as long as the key is pressed. 
// When no key is pressed, the program clears the screen, i.e. writes
// "white" in every pixel;
// the screen should remain fully clear as long as no key is pressed.

// Put your code here.
// Fill.asm: 按鍵全黑，放開全白

(LOOP)
    // 1. 檢查鍵盤狀態
    @KBD
    D=M
    @CHECK_KEY
    D;JEQ       // 若 KBD == 0，跳轉設定為白色

    // 有按鍵：設定顏色為全黑 (-1)
    @color
    M=-1
    @DRAW
    0;JMP

(CHECK_KEY)
    // 無按鍵：設定顏色為全白 (0)
    @color
    M=0

(DRAW)
    // 2. 初始化繪製變數
    @SCREEN
    D=A
    @addr
    M=D         // addr = 16384 (SCREEN 記憶體起點)

    @8192
    D=A
    @i
    M=D         // i = 8192 (螢幕所需的總 word 數)

(FILL)
    // 3. 檢查螢幕刷色是否完畢
    @i
    D=M
    @LOOP
    D;JEQ       // 若 i == 0，刷色完成，跳回 LOOP 重新監聽鍵盤

    // 4. 將 color 寫入當前螢幕記憶體位置
    @color
    D=M
    @addr
    A=M         // 切換 A 暫存器指向 RAM[addr]
    M=D         // RAM[addr] = color

    // 5. 更新指標與計數器
    @addr
    M=M+1       // addr = addr + 1
    @i
    M=M-1       // i = i - 1

    // 6. 繼續下一個 word 的刷色
    @FILL
    0;JMP