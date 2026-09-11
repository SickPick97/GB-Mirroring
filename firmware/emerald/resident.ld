OUTPUT_ARCH(arm)
ENTRY(resident_entry)
MEMORY { ram (rwx) : ORIGIN = 0x0203cf80, LENGTH = 0x2880
 hot (rwx) : ORIGIN = 0x03002950, LENGTH = 0x600 }
SECTIONS {
 .entry : { *(.entry) } > ram
 .hot : { __hot_start__ = .; *(.text*) . = ALIGN(4); LONG(0x354d4247); __hot_end__ = .; } > hot AT> ram
 __hot_load__ = LOADADDR(.hot);
 .scheduler : { *(.scheduler) } > ram
 .rodata : { *(.rodata*) } > ram
 .data : { *(.data*) } > ram
 .bss (NOLOAD) : { . = ALIGN(4); *(.bss*) *(COMMON) . = ALIGN(4); __end__ = .; } > ram
 /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment) *(.ARM.attributes) }
 ASSERT(__end__ <= 0x0203f800,"Resident overlaps stack")
}
