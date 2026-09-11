.syntax unified
.cpu arm7tdmi
.arm
.text
/* Unrolled sender: low/data then rising edge. Return clock low. */
.global fast_begin,fast_end
fast_begin:
.global sd_send_fast
sd_send_fast:
 push {r4,lr}
 ldr r2, =0x04000134
 ldr r3, =0x8030
 cmp r1, #0
 beq 3f
1: ldrh r4, [r0], #2
 .irp bit,15,14,13,12,11,10,9,8,7,6,5,4,3,2,1,0
 mov r12, r3
 tst r4, #(1 << \bit)
 orrne r12, r12, #2
 strh r12, [r2]
 orr r12, r12, #1
 strh r12, [r2]
 .endr
 subs r1, r1, #1
 bne 1b
 strh r3, [r2]
3: pop {r4,pc}
 .ltorg

fast_end:
.global hash_begin,hash_end
hash_begin:
 push {r4,r5,lr}
 mov r2,#0
 mov r3,#0
 mov r4,#64
1: ldr r5,[r0],#4
 eor r2,r5,r2,ror #27
 add r3,r5,r3,ror #25
 subs r4,r4,#1
 bne 1b
 str r2,[r1]
 str r3,[r1,#4]
 pop {r4,r5,pc}
hash_end:
