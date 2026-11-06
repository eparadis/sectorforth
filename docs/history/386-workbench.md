# Previous 386 workbench platform

Through commit `ab186a2`, the source-loaded workbench targeted a 386 or
newer CPU and a 1.44 MB floppy image. Its boot sector used `SETNZ`,
immediate-value pushes, and the later-processor behavior of `PUSH SP`.
It did not preserve BP around BIOS character output, which was sufficient
for the QEMU/SeaBIOS regression environment but not original IBM scrolling
behavior.

The floppy geometry was 80 cylinders, two heads, and 18 sectors per track,
for 2,880 sectors. The rebuildable system occupied sectors 0–63; blocks
1–1,408 occupied the remaining 1,024-byte pairs. The runtime used the same
single-segment RAM arrangement and source-loaded architecture as today.

A feasibility experiment replaced the later instructions with 8088
equivalents. The direct instruction port measured 517 bytes. Equivalent
instruction substitutions reduced it to 512 bytes, and a redundant jump
provided space for protecting BP around video output. A temporary 360 KB
image booted the workbench and passed stack and save/reload smoke tests in
QEMU on a later x86 CPU. This did not constitute actual 8088 validation.

The current [XT platform](../xt-platform.md) adopts 8088 compatibility,
512 KB of conventional RAM, and 360 KB geometry as the minimum target.
The old image format is retained only as a migration input. Occupied data
beyond the smaller image's capacity must be migrated before conversion.
