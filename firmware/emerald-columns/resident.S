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
 ldr r2,=0x03002750
 cmp r3,r2
 bne call_original
 mov r3,sp
 ldr sp,=0x0203fc00
 push {r3,lr}
 bl observe
 pop {r3,lr}
 mov sp,r3
call_original:
 ldr r3,original_irq
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

.section .scheduler,"ax"
.arm
.global column_signatures
.type column_signatures,%function
column_signatures:
 push {r4-r8,lr}
 ldr r7,=0x01000193
 mov r8,#8
1:
 mov r2,r0
 mov r3,#0
 mov r4,#4
2:
 ldm r2,{r5,r6}
 eor r3,r3,r5
 mul r3,r7,r3
 eor r3,r3,r3,lsr #16
 eor r3,r3,r6
 mul r3,r7,r3
 eor r3,r3,r3,lsr #16
 add r2,r2,#64
 subs r4,r4,#1
 bne 2b
 eor r3,r3,r3,lsr #16
 strh r3,[r1],#2
 add r0,r0,#8
 subs r8,r8,#1
 bne 1b
 pop {r4-r8,lr}
 bx lr

.ltorg
