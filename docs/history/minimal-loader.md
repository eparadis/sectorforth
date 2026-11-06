# Minimal source loader implementation

The CHS-only loader was implemented in commit `a516150`, before the
source-loaded workbench. It established that a complete 512-byte kernel
could start a sequence of Forth source sectors on a real BIOS floppy
interface without loading a binary extension.

The kernel added `boot ( -- )`, which read CHS 0/0/2 into the terminal input
buffer. Removing line editing and cross-row backspace handling provided
space for the reader. Backspace was ignored, and source sectors carried
their own space/NUL terminators. The remaining eight bytes restored the
fixed boot address after errors.

The original second sector used 498 source bytes. It built numeric
constants `0` through `10`, stack helpers, and
`load ( cylinder head sector -- )`. That word temporarily patched the
native reader's CHS operands and restored them after a successful read.

Source files could continue with explicit commands such as `0 0 4 load`.
Every load replaced the input buffer; it discarded trailing caller text
and returned to the calling compiled word before the replacement text was
interpreted. Consequently, repeatedly calling it from a loop would only
leave the last sector available for interpretation. It did not provide
nested or returning source evaluation.

The initial image builder packed a list of source files into consecutive
floppy sectors. QEMU tests verified both heads, another cylinder, source
chaining, ignored Backspace, and error recovery. There was no disk-write
path, block cache, numeric parser, or source editor.

The current bootstrap adds an explicit continuation to the foundation
files, and the workbench preserves the old source-replacement operation
under `load-chs`. Public `load` now addresses a 1,024-byte workbench block
and returns after interpreting it. Current behavior and commands are
documented in [the README](../../README.md) and
[the workbench notes](../../forth/README.md).
