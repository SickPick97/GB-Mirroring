OUTPUT_ARCH(arm)
ENTRY(_image)
MEMORY { ewram (rwx) : ORIGIN = 0x02000000, LENGTH = 256K }
SECTIONS {
  .text : { KEEP(*(.boot)) *(.text*) *(.rodata*) } > ewram
  .data : { *(.data*) } > ewram
  . = ALIGN(4);
  __bss_start__ = .;
  .bss (NOLOAD) : { *(.bss*) *(COMMON) . = ALIGN(4); } > ewram
  __bss_end__ = .;
  /DISCARD/ : { *(.comment) *(.ARM.attributes) *(.ARM.exidx*) *(.ARM.extab*) }
  ASSERT(__bss_end__ < 0x0203f000, "Multiboot exceeds EWRAM")
}
