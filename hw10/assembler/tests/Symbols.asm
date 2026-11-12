// 測試標籤、變數、跳躍
// 從 counter = 1 開始累加到 10

@counter
M=1
(LOOP)
    @counter
    D=M
    @10
    D=D-A
    @END
    D;JGT
    @counter
    M=M+1
    @LOOP
    0;JMP
(END)
@END
0;JMP
