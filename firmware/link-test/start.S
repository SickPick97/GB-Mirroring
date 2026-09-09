.syntax unified
.cpu arm7tdmi
.arm
.section .boot,"ax",%progbits
.global _image, _start
_image:
    b _start
    .space 0xbc
    b _start
    .byte 0,0
    .space 0x1a
_start:
    mov r0, #0xdf
    msr cpsr_c, r0
    ldr sp, =0x03007f00
    ldr r0, =__bss_start__
    ldr r1, =__bss_end__
    mov r2, #0
1:  cmp r0, r1
    strlo r2, [r0], #4
    blo 1b
    bl main
2:  b 2b
.ltorg
