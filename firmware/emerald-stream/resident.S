.syntax unified
.cpu arm7tdmi
.arm
.section .entry,"ax"
.global resident_entry,original_irq,vb_thunk
resident_entry: b wrapper
original_irq: .word 0
/* Installed in gMain.vblankCallback while a known scene runs: the game's copy queues are read here, inside its own
   VBlank handler, when the game had no idle time before VBlank to read them. */
vb_thunk:
 push {lr}
 bl observe
 pop {lr}
 ldr r12,=orig_vblank
 ldr r12,[r12]
 bx r12
/* Entered from the BIOS interrupt handler, which saved r0-r3, r12 and the return address ([sp,#20] is the
   interrupted pc + 4). Nothing runs before the game's own handler: HBlank, VCount, serial and timer interrupts go
   straight to it, and VBlank only after one comparison. */
wrapper:
#ifdef PASSTHROUGH
 ldr pc,original_irq
#endif
#if defined(GBM_PROFILE) || defined(SOFT)
 ldr r12,=irq_total
 ldr r0,[r12]
 add r0,r0,#1
 str r0,[r12]
#endif
 mov r12,#0x04000000
 ldr r12,[r12,#0x200]
 and r12,r12,r12,lsr #16
 tst r12,#1
 bne vblank
 cmp r12,#0x10
 beq timer1
 ldr pc,original_irq
vblank:
 ldr r0,[sp,#20]
 ldr r1,=irq_lr
 str r0,[r1]
 push {lr}
 ldr r3,original_irq
 mov lr, pc
 bx r3
 pop {lr}
 ldr r0, original_irq
 ldr r1, =0x03002750
 cmp r0,r1
 bxne lr
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
 ldr r12,=tick
 b nested
/* Timer 1 is only ever enabled by the resident. Idle means: interrupted inside the game's WaitForVBlank loop
   (0x080008c6-0x080008ce: Emerald spins on gMain.intrCheck instead of halting in the BIOS) with the VBlank flag
   still clear, i.e. the frame's work is done and the game waits for the next VBlank. */
timer1:
 mov r1,#0x04000000
 add r1,r1,#0x200
 mov r0,#0x10
 strh r0,[r1,#2]
 ldr r0,[sp,#20]
 ldr r1,=0x080008ca
 sub r0,r0,r1
 cmp r0,#8
 bxhi lr
 ldr r0,=0x030022dc
 ldrh r0,[r0]
 tst r0,#1
 bxne lr
 ldr r12,=idle
/* Runs r12 in system mode on the interrupted context's stack with interrupts enabled, so the game's interrupts are
   serviced (through this wrapper and the game handler) while the resident works. Never re-entered. */
nested:
 ldr r0,=in_work
 ldr r1,[r0]
 cmp r1,#0
 beq 3f
 ldr r0,=tick
 cmp r12,r0
 ldreq r0,=tick_owed
 moveq r1,#1
 streq r1,[r0]
 cmp r1,#0
3:
#if defined(GBM_PROFILE) || defined(SOFT)
 beq 2f
 ldr r0,=collisions
 ldr r1,[r0]
 add r1,r1,#1
 str r1,[r0]
 bx lr
2:
#else
 bxne lr
#endif
 mov r1,#1
 str r1,[r0]
 mrs r0,spsr
 push {r0,lr}
 mrs r0,cpsr
 bic r0,r0,#0xdf
 orr r0,r0,#0x1f
 msr cpsr_c,r0
 push {lr}
 mov lr,pc
 bx r12
 pop {lr}
 mrs r0,cpsr
 orr r0,r0,#0x80
 msr cpsr_c,r0
 bic r0,r0,#0x1f
 orr r0,r0,#0x12
 msr cpsr_c,r0
 pop {r0,lr}
 msr spsr_fsxc,r0
 ldr r0,=in_work
 mov r1,#0
 str r1,[r0]
 bx lr
.ltorg
#if defined(GBM_PROFILE) || defined(SOFT)
.section .bss
.global irq_total,collisions
irq_total: .word 0
collisions: .word 0
#endif
