# =============================================================================
# start.S - Doan khoi dong: dat con tro ngan xep, gp, xoa .bss roi goi main()
# CPU bat dau chay tai dia chi 0x0000_0000 (PROGADDR_RESET).
# =============================================================================
    .section .text.start
    .global _start
_start:
    .option push
    .option norelax
    la      gp, __global_pointer$
    .option pop
    la      sp, __stack_top          # dinh RAM (16 KB)

    la      t0, __bss_start          # xoa vung .bss ve 0
    la      t1, __bss_end
1:  bgeu    t0, t1, 2f
    sw      zero, 0(t0)
    addi    t0, t0, 4
    j       1b
2:
    call    main
3:  j       3b                       # main() khong bao gio tra ve; neu co thi dung tai day
