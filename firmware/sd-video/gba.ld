OUTPUT_ARCH(arm)
ENTRY(_image)
MEMORY {
 ewram (rwx) : ORIGIN = 0x02000000, LENGTH = 256K
 iwram (rwx) : ORIGIN = 0x03000000, LENGTH = 28K
}
SECTIONS {
 .boot : { KEEP(*(.boot)) } > ewram
 .iwram : { __iwram_start__ = .; *(.text*) *(.rodata*) . = ALIGN(4); __iwram_end__ = .; } > iwram AT> ewram
 __iwram_load__ = LOADADDR(.iwram);
 .data : { *(.data*) } > ewram
 .bss (NOLOAD) : { . = ALIGN(4); __bss_start__ = .; *(.bss*) *(COMMON) . = ALIGN(4); __bss_end__ = .; } > ewram
 /DISCARD/ : { *(.comment) *(.ARM.attributes) *(.ARM.exidx*) *(.ARM.extab*) }
 ASSERT(__bss_end__ < 0x0203f000, "EWRAM overflow")
}
