.syntax unified
.cpu arm7tdmi
.arm
.text
.global _start
_start:
 ldr r1,=0x04000208
 mov r0,#0
 strh r0,[r1]
 mov r0,#0x12
 msr cpsr_c,r0
 ldr sp,=0x03007fa0
 mov r0,#0x1f
 msr cpsr_c,r0
 ldr sp,=0x03007e40
 mov r0,#0xfe
 swi 0x010000
 mov r0,#0x02000000
 ldr r1,=0x0203cf80
 mov r2,#0
1: str r2,[r0],#4
 cmp r0,r1
 blo 1b
 ldr r0,=0x08000248
 ldr r1,=0x03007ffc
 str r0,[r1]
 mov r0,#0x05000000
 ldr r1,=0x7fff
 strh r1,[r0]
 ldr r0,=0x08000fe5
 mov lr,pc
 bx r0
 ldr r0,=0x04000204
 ldr r1,=0x4014
 strh r1,[r0]
 ldr r0,=0x080005bd
 mov lr,pc
 bx r0
 ldr r0,=0x08000685
 mov lr,pc
 bx r0
 ldr r1,=0x04000208
 mov r0,#0
 strh r0,[r1]
 ldr r1,=0x03007ffc
 ldr r0,[r1]
 ldr r2,=0x0203cf80
 str r0,[r2,#4]
 str r2,[r1]
 ldr r1,=0x04000208
 mov r0,#1
 strh r0,[r1]
 sub sp,sp,#24
 ldr r0,=0x080003cf
 bx r0
 .ltorg
