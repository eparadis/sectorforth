# Source loaded Forth workbench

The numbered `.f` files are the default source chain after `bootstrap.f`.
Each file fits in one sector after whitespace folding and terminators.
Keep the files in numeric order. The default image contains 27 sectors of
boot and source code, followed by unused bootstrap space and workbench data.
The platform target is an 8088 XT compatible with 512 KB of conventional
RAM and an 80-column text display. The image is a 360 KB floppy.

## Example session

Start the default image with `make run`, or boot its floppy image on the
machine. After the BIOS displays `Booting from Floppy...`, the initial
interpreter waits on a blank line with no readiness prompt. Click inside
the QEMU display, type lowercase `boot`, and press Enter. The characters
should echo in that display, rather than in the terminal running Make.

Loading the source chain has no progress display. A local QEMU startup
took about 41 seconds after Enter before `sf> ` appeared. Wait for that
prompt before entering more commands; the silent pause is expected.

In the transcripts below, type only the text after `sf>` or `edit>` and
press Enter. Those prefixes are prompts, not part of the command. `boot`
and the unprefixed `workbench` below are also typed input, at the initial
interpreter which prints no prompt. Other unprefixed lines show output.
Trailing spaces and blank listing lines are omitted.

Start with arithmetic and a definition:

```text
boot
sf> 2 3 + .
5
sf> 7 dup + .
14
sf> : answer 40 2 + ;
sf> answer .
42
```

Numbers are pushed onto the data stack. `+` consumes two values and leaves
their sum; `.` prints and consumes the top value. Definitions made with
`: name ... ;` remain available in RAM until the machine is reset.

Storage and conditionals work too:

```text
sf> variable counter
sf> 41 counter !
sf> 1 counter +!
sf> counter @ .
42
sf> : nonzero? if 1 else 0 then ;
sf> 7 nonzero? .
1
sf> 0 nonzero? .
0
```

Here `counter` pushes the address of its storage. `!` stores a value, `@`
fetches it, and `+!` adds to it. Control words such as `if` belong inside
a compiled definition.

### Edit and save source on disk

Use an unused block for this part. The example uses block 1 and replaces
its contents. `blank-block` fills it with spaces, and `edit-line` replaces
one line, numbered 0 through 15, with up to 64 characters:

```text
sf> 1 blank-block
sf> 0 1 edit-line
edit> : answer 40 2 + ;
sf> 1 1 edit-line
edit> answer .
sf> save-buffers
sf> flush
sf> 1 list
: answer 40 2 + ;
answer .
sf> 1 load
42
sf> answer .
42
```

At `edit>`, enter Forth source to store; it is not executed by the editor.
`list` displays the block without running it. `load` interprets the block,
so its first line defines `answer` and its second line prints the result.
`save-buffers` writes changes to disk; `flush` also drops the cached block.

After resetting the machine, the saved source is still on disk. Load it
again to recreate its definitions in RAM:

```text
boot
sf> 1 load
42
sf> answer .
42
```

Save edits before stopping or resetting the machine. Image rebuilds
preserve saved blocks, while `make fresh-image` explicitly erases them.

### Recover after an error

A missing word prints `!!` and returns to the first-sector input loop.
That loop has no `sf>` prompt. Type `workbench`, rather than bootstrapping
again, to resume:

```text
sf> missing-word
!!
workbench
sf> 1 load
42
```

Completed definitions remain available, but the data stack is cleared.
Dirty block edits also remain in RAM; save them after recovering.

## Available words at the workbench prompt

These are useful public words after `boot`; names are lowercase and
case-sensitive. A dictionary listing (`words`) and stack display (`.s`)
are future additions, so use this reference to choose commands.

| Task | Words | Example |
| --- | --- | --- |
| Stack manipulation | `dup drop swap over nip rot -rot 2dup 2drop` | `7 dup + .` prints `14`. |
| Arithmetic | `+ - negate 1+ 1- 2* 256* u/mod` | `17 5 u/mod . .` prints quotient `3`, then remainder `2`. |
| Logic and comparisons | `and or xor nand invert = <> 0= 0<> < > u< u>` | `4 4 = .` prints true as `-1`. |
| Definitions and control | `: ; if else then begin until again while repeat recurse` | `: twice dup + ;` defines a word. |
| Storage and memory | `variable constant create allot @ ! c@ c! +! move fill` | `123 constant limit` defines a constant. |
| Display and input | `. u. emit type cr space key accept` | `65 emit cr` prints `A` and a newline. |
| Source blocks | `blank-block edit-line list load thru` | `1 load` runs saved block 1; `thru` accepts an inclusive range of saved blocks. |
| Buffer management | `block buffer update save-buffers flush` | `save-buffers` saves the dirty block buffer. |
| Source evaluation | `evaluate sector-evaluate sector-thru sector-load next-source load-chs` | `sector-evaluate` loads a numbered source sector and resumes its caller. |
| Raw sectors | `read-sector write-sector` | Use the explicit buffer and I/O-result interfaces described below. |

Use block commands for the editing session above. Sector commands address
the image's physical layout and are mainly useful when extending the
bootstrap. `next-source` is a continuation inside disk source, not a
standalone command to enter at `sf>`.

## Source groups

| Files | Purpose |
| --- | --- |
| 01–07 | Stack and memory helpers, compiler control, constants, unsigned arithmetic, logical sector conversion, and `next-source`. |
| 08–10 | Memory copying, bounded parsing, and dictionary lookup. |
| 11–13 | Decimal conversion, literal compilation, and the Forth interpreter. |
| 14–15 | Returning evaluation and bounded definition-name parsing. |
| 16–19 | Raw disk I/O, source loading, and returning sector/range evaluation. |
| 20–22 | One-buffer block storage, saves, inspection, and returning block/range loading. |
| 23–25 | Character input, line editing, numeric output, and the `sf>` loop. |

The first foundation files use explicit CHS continuation until logical
loading exists. File 07 initializes `source-sector` to its own logical
address. Later files continue with `next-source`; once the Forth
interpreter exists, `enter-next` reads and interprets the next source before
returning. The final file starts `workbench`. Appended application sectors
are invoked explicitly with `sector-evaluate`.

## Returning evaluation

`evaluate ( address length -- )` accepts at most 4,094 bytes and treats its
argument as memory source. `(evaluate)` backs up the active input region,
its length, and `>in`, interprets the supplied region, and restores the
caller before returning. Definitions and stack results survive. Compilation
state follows the actions of the evaluated source rather than being reset
on return.

Public `evaluate` temporarily clears the disk-source context and `blk`.
`sector-evaluate` establishes a logical-sector context, and block `load`
establishes `blk`. Each restores its caller's context. A tail `next-source`
replaces the active disk source while its interpretation continues.
`sector-thru` and `thru` keep their iteration state on the return stack so
results left by loaded source do not disturb the range.

Four evaluation frames are available, including the frame used for each
interactive command. Oversized regions, excessive depth, invalid source
addresses, bad numeric input, and missing names use the kernel error/reset
path. Reenter `workbench` after `!!`; this version does not automatically
restart its input loop after an abort. Start the complete bootstrap once
per machine reset.

`execute` uses a two-cell dispatch thread containing the chosen execution
token and `exit`. Nested execution can replace the first cell after it has
been fetched; the continuation cell remains fixed. The bootstrap's `lit`
is an internal inline-cell reader, not standard `[']`.

## Raw disk I/O

`read-sector ( sector destination -- ior )` and
`write-sector ( sector source -- ior )` transfer exactly 512 bytes without
selecting an input source. Zero means success, BIOS AH status reports disk
errors, and -1 reports an invalid logical address. Raw reads permit sector
0; writes reject it. Callers supply valid buffers and must not overwrite
live interpreter memory. Geometry is fixed at 40 cylinders, two heads, and
nine sectors per track: logical sectors 0–719. `load-chs` accepts cylinders
0–39, heads 0–1, and one-based sectors 1–9. Source loaders reject the boot
sector even though raw reads permit it.

The raw bridge reuses the boot sector's BIOS instruction sequence. It
saves its first 19 bytes, temporarily substitutes stack-fed register setup
and status capture, performs the operation, and restores the original
bytes before returning, including on a BIOS error. This preserves the
saved BIOS boot-drive number. No binary extension is loaded from disk.

The operand offsets and short error branch are checked by NASM in
`sectorforth.asm`. The decimal patch values encode these instruction pairs:

| Value | Bytes | Meaning |
| --- | --- | --- |
| 36955 | `5b 90` | `pop bx`, `nop` |
| 36953 | `59 90` | `pop cx`, `nop` |
| 36954 | `5a 90` | `pop dx`, `nop` |
| 37008 | `90 90` | Two no-ops |
| 36944 | `50 90` | `push ax`, `nop` |

The bridge replaces the failure branch with no-ops and returns AX on the
data stack instead of changing `>in`. It extracts the BIOS status after
restoring the reader. The code assumes BIOS preservation of the Forth
instruction pointer and return-stack register, as the existing reader does.
There is no disk retry policy yet.

The boot sector is assembled with `CPU 8086`, including an explicit
snapshot of SP before pushing it for `sp@`, and register-based constant
pushes. Its character output saves BP around `INT 10h` because original
IBM BIOS scrolling uses that register. The disk bridge's instruction bytes
already belong to the 8086/8088 instruction set. The kernel remains 512 bytes.

## Memory layout

Addresses below are offsets in the kernel's segment, whose physical base
is 0x0500. These fixed buffers do not allocate space in the dictionary.
The platform assumes 512 KB is installed, but this runtime still uses one
64 KB segment. Its data-stack origin is unchanged at `fffe`; a 64 KB-only
original PC is outside the supported target.

| Segment offsets | Use |
| --- | --- |
| `0000–0fff` | Terminal input buffer |
| `1000–1003` | Kernel state and parsing offset |
| `1004–5003` | Four evaluation backups, each reserving 4 KB |
| `5004–5403` | The 1,024-byte block buffer |
| `5404–5603` | The 512-byte sector-source buffer |
| `5604–76fe` | Space below the downward-growing return stack |
| `7700–78ff` | Boot sector and native variables |
| `7900` upward | Compiled dictionary, sharing remaining space with the data stack growing downward from `fffe` |

Evaluation copies only the active parent input plus its terminators into
the reserved frame. These buffers stay below the return stack; the depth
limit prevents evaluation frames from entering the block buffer. General
dictionary/stack collision detection is still future work.

## Disk layout and persistence

Logical sectors 0–63 form the rebuildable system area. Workbench block 1
uses sectors 64 and 65; block 328 uses sectors 718 and 719. Block 0 is
invalid. Source packing rejects a list that would enter the data area.

`block` reads on a cache miss and saves a dirty block before eviction.
`buffer` assigns the same buffer without reading it. `update` marks it
dirty, `save-buffers` writes its two sectors, and `flush` saves and
invalidates the cache. A failed save leaves the dirty flag set. Saves are
not transactional across both sectors.

`list` displays sixteen lines of 64 characters without interpreting them.
`edit-line ( line block -- )` blanks and replaces one such line from the
keyboard, then marks the block dirty. A 64-character line plus the editor
prompt fits within the BIOS text row, including Backspace editing.

The image builder preserves the data area when rebuilding an existing
image. It also preserves fitting blocks when converting a previous 1.44 MB
image, and refuses conversion if the truncated region contains nonzero
data. `make clean` removes assembler outputs but keeps the image;
`make fresh-image` intentionally erases saved blocks. Keep QEMU stopped
while rebuilding its image.

## Compatibility work still ahead

This is a small workbench, not a claim of Forth conformance. It still uses
case-sensitive names and decimal-only conversion. Bootstrap numeric words
remain visible, so hexadecimal parsing must retire those names first.
`here` retains the kernel's pointer-variable interface; stack and dictionary
bounds are not checked. The compiler still relies on native colon and
semicolon words. Comments, string literals, full Core arithmetic, standard
exception handling, and a complete block editor remain on the roadmap.

The image packer still folds whitespace. Source programs must use the
dictionary and text format currently available; the commented example
files cannot simply be packed unchanged. `move` handles overlapping
regions; `cmove` and `cmove>` provide explicit forward and backward copies.

`make test` covers the first-sector loader, logical continuation, nested
and range evaluation, literal compilation, block editing and saves,
nested block loading, reboot persistence, write protection, and preservation
of saved data across image rebuilds. Real-hardware validation remains a
separate step.
QEMU uses a 486 model and 16 MB for SeaBIOS compatibility; it does not
validate an 8088 or a 512 KB firmware environment. See
[the XT platform notes](../docs/xt-platform.md).
