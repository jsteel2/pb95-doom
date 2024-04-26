MEMORY
{
    ROM (x)   : ORIGIN = 0, LENGTH = 0x100000 /* 1024k */
    RAM (xrw) : ORIGIN = 0x00400000, LENGTH = 0x800000	/* 8192k */
}
ENTRY(_start)
SECTIONS {
    __stacktop = ORIGIN(RAM) + LENGTH(RAM);
    .text :
    {
        . = ALIGN(4);
        *(.text.start)
        *(.text)
        *(.text*)
        . = ALIGN(4);
        _etext = .;
    } >ROM
    .data :
    {
        . = ALIGN(4);
        _sdata = .;
        _ram_start = .;
        . = ALIGN(4);
        *(.data)
        *(.data*)
        *(.sdata)
        *(.sdata*)
        *(.rodata)
        *(.rodata*)
        *(.srodata)
        *(.srodata*)
        . = ALIGN(4);
        _edata = .;
    } >RAM
    .bss :
    {
        . = ALIGN(4);
        _sbss = .;
        *(.bss)
        *(.bss*)
        *(.sbss)
        *(.sbss*)
        *(COMMON)
        . = ALIGN(4);
        _ebss = .;
    } >RAM
    .heap :
    {
        . = ALIGN(4);
        _heap_start = .;
    } >RAM
}
