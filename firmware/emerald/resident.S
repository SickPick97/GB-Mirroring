.syntax unified
.cpu arm7tdmi
.arm
.section .entry,"ax"
.global resident_entry,original_irq
resident_entry: b wrapper
original_irq: .word 0
wrapper:
 push {r0-r3,r12,lr}
 ldr r3, original_irq
 mov lr, pc
 bx r3
 ldr r0, original_irq
 ldr r1, =0x03002750
 cmp r0,r1
 bne no_tick
 ldr r0,=__hot_load__
 ldr r1,=__hot_start__
 ldr r2,[r0]
 ldr r3,[r1]
 cmp r2,r3
 bne copy_hot
 ldr r2,=__hot_end__-4
 ldr r2,[r2]
 ldr r3,=0x354d4247
 cmp r2,r3
 beq ready
copy_hot:
 ldr r2,=__hot_end__
1: ldr r3,[r0],#4
 str r3,[r1],#4
 cmp r1,r2
 blo 1b
ready:
 mov r3, sp
 ldr sp, =0x0203fc00
 push {r3,lr}
 bl tick
 pop {r3,lr}
 mov sp, r3
no_tick:
 pop {r0-r3,r12,lr}
 bx lr
.ltorg
