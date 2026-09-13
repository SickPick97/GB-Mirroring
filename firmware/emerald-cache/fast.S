.syntax unified
.cpu arm7tdmi
.arm
.text
/* Unrolled sender: low/data then rising edge. Return clock low. */
.global fast_begin,fast_end
.type fast_begin, %function
fast_begin:
.global sd_send_fast
.type sd_send_fast, %function
sd_send_fast:
 push {r4,r5,lr}
 ldr r2, =0x04000134
 ldr r3, =0x8030
 cmp r1, #0
 beq 3f
1: ldrh r4, [r0], #2
 mov r5,#4
2:
 .irp bit,15,14,13,12
 mov r12, r3
 tst r4, #(1 << \bit)
 orrne r12, r12, #2
 strh r12, [r2]
 orr r12, r12, #1
 strh r12, [r2]
 .endr
 lsl r4,r4,#4
 subs r5,r5,#1
 bne 2b
 subs r1, r1, #1
 bne 1b
 strh r3, [r2]
3: pop {r4,r5,lr}
 bx lr
 .ltorg

fast_end:
.global hash_begin,hash_end
.type hash_begin, %function
hash_begin:
 push {r4,r5,lr}
 mov r2,#0
 mov r3,#0
 mov r4,#16
1:
 .rept 4
 ldr r5,[r0],#4
 eor r2,r5,r2,ror #27
 add r3,r5,r3,ror #25
 .endr
 subs r4,r4,#1
 bne 1b
 str r2,[r1]
 str r3,[r1,#4]
 pop {r4,r5,lr}
 bx lr
hash_end:

/* Skip unchanged blocks entirely in IWRAM. r2=NULL forces a keyframe. */
.global scan_next
.type scan_next, %function
scan_next:
 push {r4-r10,lr}
 mov r4,r0
 mov r5,r1
 mov r6,r2
 mov r7,r3
 ldr r9,=0x04000006
1:
 cmp r4,#392
 movhi r4,#392
 addhi r4,r4,#1
 bhi 4f
 ldrh r0,[r9]
 cmp r0,#160
 orrlo r4,r4,#0x80000000
 blo 4f
 cmp r0,#224
 orrhs r4,r4,#0x80000000
 bhs 4f
 ldr r0,=dirty_mask
 mov r1,r4,lsr #5
 ldr r2,[r0,r1,lsl #2]
 cmp r2,#0
 bne mask_nonzero
 add r4,r4,#32
 bic r4,r4,#31
 b 1b
mask_nonzero:
 and r1,r4,#31
 mov r3,#1
 tst r2,r3,lsl r1
 beq skip_clean
 cmp r4,#0
 moveq r8,r5
 beq 2f
 cmp r4,#5
 sublo r8,r4,#1
 movlo r8,r8,lsl #8
 addlo r8,r8,#0x05000000
 blo 2f
 cmp r4,#9
 sublo r8,r4,#5
 movlo r8,r8,lsl #8
 addlo r8,r8,#0x07000000
 subhs r8,r4,#9
 movhs r8,r8,lsl #8
 addhs r8,r8,#0x06000000
2:
 mov r0,r8
 mov r1,r7
 bl hash_begin
 cmp r6,#0
 beq 3f
 ldm r7,{r0,r1}
 add r2,r6,r4,lsl #3
 ldm r2,{r2,r3}
 cmp r0,r2
 cmpeq r1,r3
 bne 3f
 ldr r0,=dirty_mask
 mov r1,r4,lsr #5
 ldr r2,[r0,r1,lsl #2]
 and r3,r4,#31
 mov r10,#1
 bic r2,r2,r10,lsl r3
 str r2,[r0,r1,lsl #2]
skip_clean:
 add r4,r4,#1
 b 1b
3:
 str r8,[r7,#8]
4:
 mov r0,r4
 pop {r4-r10,lr}
 bx lr
.ltorg
