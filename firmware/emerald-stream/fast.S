.syntax unified
#ifndef DEADLINE
#define DEADLINE 20
#endif
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

/* r0=halfwords, r1=count: CRC-32 (reflected, poly 0xedb88320) of the little-endian halfwords, four bits a step. */
.global crc32_arm
.type crc32_arm, %function
crc32_arm:
 push {r4,lr}
 mvn r2,#0
 adr r3,crc_nibbles
 subs r1,r1,#0
 beq 2f
1:
 ldrh r4,[r0],#2
 eor r2,r2,r4
 .rept 4
 and r4,r2,#15
 ldr r4,[r3,r4,lsl #2]
 eor r2,r4,r2,lsr #4
 .endr
 subs r1,r1,#1
 bne 1b
2:
 mvn r0,r2
 pop {r4,lr}
 bx lr
crc_nibbles:
 .word 0,0x1db71064,0x3b6e20c8,0x26d930ac,0x76dc4190,0x6b6b51f4,0x4db26158,0x5005713c
 .word 0xedb88320,0xf00f9344,0xd6d6a3e8,0xcb61b38c,0x9b64c2b0,0x86d3d2d4,0xa00ae278,0xbdbdf21c
fast_end:
.global hash_begin,hash_end
.type hash_begin, %function
hash_begin:
 push {r4-r12,lr}
 mov r2,#0
 mov r3,#0
 mov r4,#8
 ldr lr,=0x9e3779b1
1:
 ldmia r0!,{r5-r12}
 /* h0: multiply chain (word-wise FNV-1a), order and position dependent; h1: add-rotate. An xor-rotate h0 used
    before 0.13 ignored solid-colour words (0x11111111 rotated cancels itself) and swapped block halves. */
 .irp reg,r5,r6,r7,r8,r9,r10,r11,r12
 eor r2,r2,\reg
 mul r2,lr,r2
 add r3,\reg,r3,ror #25
 .endr
 eor r2,r2,r2,lsr #15
 add r3,r3,r3,lsl #7
 subs r4,r4,#1
 bne 1b
 str r2,[r1]
 str r3,[r1,#4]
 pop {r4-r12,lr}
 bx lr
.ltorg
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
 ldr r0,=scan_stop
 ldr r0,[r0]
 cmp r4,r0
 bhs 4f
 ldrh r0,[r9]
 ldr r1,=entry_line
 ldr r1,[r1]
 subs r0,r0,r1
 addlo r0,r0,#228
 ldr r2,=scan_limit
 ldr r2,[r2]
 cmp r0,r2
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
 ldr r2,=0x9e3779b1
 mul r3,r1,r2
 eor r0,r0,r3
 ldr r2,[r6,r4,lsl #2]
 cmp r0,r2
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

/* r0=dirty_mask, r1=strong_mask: strong &= dirty; returns popcount(strong) over 13 words. */
.global pending_count
.type pending_count, %function
pending_count:
 push {r4-r10,lr}
 ldr r8,=0x55555555
 ldr r9,=0x33333333
 ldr r10,=0x0f0f0f0f
 mov r7,#0
 mov r6,#13
1:
 ldr r2,[r0],#4
 ldr r3,[r1]
 and r3,r3,r2
 str r3,[r1],#4
 and r4,r8,r3,lsr #1
 sub r3,r3,r4
 and r4,r3,r9
 and r3,r9,r3,lsr #2
 add r3,r3,r4
 add r3,r3,r3,lsr #4
 and r3,r3,r10
 add r3,r3,r3,lsr #8
 add r3,r3,r3,lsr #16
 and r3,r3,#63
 add r7,r7,r3
 subs r6,r6,#1
 bne 1b
 mov r0,r7
 pop {r4-r10,lr}
 bx lr
.ltorg

/* r0=a, r1=b, r2=byte count (multiple of 4, > 0): 1 when both word ranges are equal. */
.global words_equal
.type words_equal, %function
words_equal:
 push {r4,lr}
 cmp r2,#0
 beq 2f
1:
 ldr r3,[r0],#4
 ldr r4,[r1],#4
 cmp r3,r4
 bne 2f
 subs r2,r2,#4
 bne 1b
 mov r0,#1
 pop {r4,lr}
 bx lr
2:
 mov r0,#0
 pop {r4,lr}
 bx lr
.ltorg

/* r0=dst, r1=src (both halfword aligned, src word aligned), r2=halfword count. */
.global copy16
.type copy16, %function
copy16:
 push {r4-r10,lr}
 tst r0,#2
 bne 3f
1:
 cmp r2,#16
 blo 3f
 ldmia r1!,{r3-r10}
 stmia r0!,{r3-r10}
 sub r2,r2,#16
 b 1b
3:
 cmp r2,#0
 beq 5f
4:
 ldrh r3,[r1],#2
 strh r3,[r0],#2
 subs r2,r2,#1
 bne 4b
5:
 pop {r4-r10,lr}
 bx lr
.ltorg

/* r0=layer base (2 KB tile map), r1=out: 16 column-pair then 16 row-pair signatures (halfwords).
   A column pair is word g of every row; a row pair is two consecutive rows. Multiply-xorshift mixing. */
.global sb_sig
.type sb_sig, %function
sb_sig:
 push {r4-r11,lr}
 sub sp,sp,#64
 mov r2,#0
 mov r4,#0
1:
 str r2,[sp,r4,lsl #2]
 add r4,r4,#1
 cmp r4,#16
 bne 1b
 mov r12,r1
 mov r5,r0
 ldr r0,=0xc2b3
 mov r4,#0
 mov r9,#0
2:
 tst r4,#1
 moveq r9,#0
 mov r6,#0
3:
 ldr r7,[r5,r6,lsl #2]
 ldr r8,[sp,r6,lsl #2]
 eor r8,r8,r7
 mul r2,r8,r0
 eor r8,r2,r2,lsr #13
 str r8,[sp,r6,lsl #2]
 eor r9,r9,r7
 mul r2,r9,r0
 eor r9,r2,r2,lsr #13
 add r6,r6,#1
 cmp r6,#16
 bne 3b
 tst r4,#1
 beq 4f
 eor r10,r9,r9,lsr #16
 mov r11,r4,lsr #1
 add r11,r11,#16
 add r3,r12,r11,lsl #1
 strh r10,[r3]
4:
 add r5,r5,#64
 add r4,r4,#1
 cmp r4,#32
 bne 2b
 mov r6,#0
5:
 ldr r8,[sp,r6,lsl #2]
 eor r8,r8,r8,lsr #16
 add r3,r12,r6,lsl #1
 strh r8,[r3]
 add r6,r6,#1
 cmp r6,#16
 bne 5b
 add sp,sp,#64
 pop {r4-r11,lr}
 bx lr
.ltorg

/* r0=previous copy (halfwords), r1=patch body (8 mask halfwords, then the changed values), r2=halfword count.
   Applies the patch to the copy touching only the words that changed. */
.global patch_apply
.type patch_apply, %function
patch_apply:
 push {r4-r7,lr}
 add r3,r1,#16
 mov r4,r2,lsr #4
1:
 ldrh r5,[r1],#2
 mov r6,#16
2:
 movs r5,r5,lsr #1
 ldrhcs r7,[r3],#2
 strhcs r7,[r0]
 add r0,r0,#2
 subs r6,r6,#1
 bne 2b
 subs r4,r4,#1
 bne 1b
 pop {r4-r7,lr}
 bx lr
.ltorg
