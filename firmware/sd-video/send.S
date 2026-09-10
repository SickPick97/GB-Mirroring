.syntax unified
.cpu arm7tdmi
.arm
.text
.global sd_send_start,sd_send_end
sd_send_start:
 push {r4,r5,lr}
 ldr r2, =0x04000134
 ldr r3, =0x8030
1: ldrh r4, [r0], #2
 mov r5, #16
2: mov r12, r4, lsr #15
 and r12, r12, #1
 orr r12, r3, r12, lsl #1
 strh r12, [r2]
 orr r12, r12, #1
 strh r12, [r2]
 bic r12, r12, #1
 strh r12, [r2]
 mov r4, r4, lsl #1
 subs r5, r5, #1
 bne 2b
 subs r1, r1, #1
 bne 1b
 pop {r4,r5,pc}
 .ltorg
sd_send_end:

.global sd_send_slow
sd_send_slow:
 push {r4,r5,lr}
 ldr r2, =0x04000134
 ldr r3, =0x8030
1: ldrh r4, [r0], #2
 mov r5, #16
2: mov r12, r4, lsr #15
 and r12, r12, #1
 orr r12, r3, r12, lsl #1
 strh r12, [r2]
 nop
 nop
 nop
 nop
 orr r12, r12, #1
 strh r12, [r2]
 nop
 nop
 nop
 nop
 bic r12, r12, #1
 strh r12, [r2]
 nop
 nop
 nop
 nop
 mov r4, r4, lsl #1
 subs r5, r5, #1
 bne 2b
 subs r1, r1, #1
 bne 1b
 pop {r4,r5,pc}
 .ltorg
