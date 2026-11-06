# IBM XT platform target

The minimum supported target is an IBM PC/XT compatible with an 8088 CPU,
512 KB of conventional RAM, BIOS disk/keyboard/video services, and an
80-column MDA or CGA text display. The boot medium is a 360 KB double-sided
floppy with 40 cylinders, two heads, nine sectors per track, and 512-byte
sectors. The system boots directly and does not need DOS.

512 KB is a platform assumption rather than a boot-time RAM check. The
runtime retains its single 64 KB segment at physical base 0x0500, including
the original data-stack origin. Supporting a 64 KB-only original PC is not
part of this target; the remaining installed memory is available for later
extensions.

## Kernel compatibility

NASM's `CPU 8086` directive rejects later instruction encodings. The
kernel replaces `SETNZ` with `CMP AX,1` and `SBB AX,AX`, producing -1 for
zero and 0 otherwise. Immediate pushes use a register instead.

`sp@` explicitly copies SP into AX before pushing it. The original 8088
pushes a different value for `PUSH SP` than later processors; leaving that
instruction unchanged would break the Forth stack model. See
[Intel's compatibility notes](https://www.intel.com/content/dam/support/us/en/documents/processors/pentium4/sb/25366821.pdf)
and [NASM's instruction list](https://www.nasm.us/doc/nasmaf.html).

Character output preserves BP around `INT 10h`. The original IBM PC BIOS
scroll routine uses BP without saving it, while sectorforth uses BP for
its return stack. The
[published BIOS listing transcription](https://raw.githubusercontent.com/philspil66/IBM-PC-BIOS/main/PCBIOS.ASM)
shows this path in `WRITE_TTY`, `SCROLL_POSITION`, and `VIDEO_RETURN`.

The boot sector remains exactly 512 bytes. Space comes from equivalent
instruction substitutions and removing a jump into the immediately
following `NEXT` routine. No primitive is removed. The source-loaded disk
bridge keeps its checked operand offsets and uses only 8088-compatible
instructions.

## Disk geometry and saved blocks

The image builder produces 368,640 bytes, or 720 logical sectors. Forth
address conversion and range checks use the same geometry. Source loaders
reject sector 0; raw reads may inspect it, and raw writes reject it.

Logical sectors 0–63 remain the rebuildable system area. Blocks 1–328
occupy the remaining sectors in 1,024-byte pairs; block 328 ends at sector
719. Rebuilds preserve saved block data.

When opening an old 1.44 MB image, the builder preserves its fitting data
area and converts the image only if every byte beyond the 360 KB boundary
is zero. Otherwise it reports an error and leaves the old image untouched.
Those blocks must be migrated before converting. `make fresh-image`
explicitly discards saved data instead.

## Validation

The regular tests assemble the actual kernel under `CPU 8086` and check
its 512-byte size/signature, source packing, geometry boundaries, zero
comparison and stack behavior, nested evaluation, editing, saving,
reloading after restart, write protection, and image migration.

QEMU regression tests use a 486 model with 16 MB of RAM. In the installed
QEMU build, SeaBIOS fails before guest startup with 512 KB, including with
a later CPU model. That firmware limitation does not change the XT hardware
requirement, but these tests do not establish actual 8088 timing or a
512 KB boot environment.

End-to-end validation on an 8088 XT emulator and XT BIOS remains pending.
It should exercise 80-column MDA/CGA output through screen scrolling,
head and cylinder boundaries, the final sector/block, write errors, and
bootstrap performance at 4.77 MHz. Existing QEMU keyboard injection and
VGA-memory inspection are a regression interface, not an XT hardware model.

The previous platform is recorded in
[the 386 workbench history](history/386-workbench.md).
