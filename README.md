# sectorforth

sectorforth is a 16-bit x86 Forth that fits in a 512-byte boot sector.

The minimum target is an **IBM XT compatible with an 8088 processor and
512 KB of conventional RAM**, BIOS keyboard/video/disk services, and an
80-column MDA or CGA text display. The default disk is a bootable 360 KB
5.25-inch double-sided floppy: 40 cylinders, two heads, nine sectors per
track, and 512 bytes per sector. DOS is not required.

Inspiration to write sectorforth came from a 1996
[Usenet thread](https://groups.google.com/g/comp.lang.forth/c/NS2icrCj1jQ)
(in particular, Bernd Paysan's first post on the thread).

## Batteries not included

sectorforth contains the eight primitives outlined in the Usenet post
above, five variables for manipulating internal state, two I/O primitives,
and a disk-source loader named `boot`.

With that minimal set of building blocks, words for branching, compiling,
manipulating the return stack, etc. can all be written in Forth itself
(check out the examples!).

The colon compiler (`:`) is available, so new words can be defined easily
(that means `;` is also there, of course).

The first-sector interpreter does not convert unknown words to numbers.
The source-loaded workbench adds decimal numeric input and literal
compilation using those same primitives.

Typing `boot` loads the second sector of the boot disk as Forth source.
The included [bootstrap.f](bootstrap.f) builds numeric constants and a
CHS-addressed source loader, so additional source sectors can extend the
dictionary without loading binary instructions from disk. The default
image continues through [forth/](forth/README.md) to a small disk workbench.

### Primitives

| Primitive | Stack effects | Description                                   |
| --------- | ------------- | --------------------------------------------- |
| `@`       | ( addr -- x ) | Fetch memory contents at addr                 |
| `!`       | ( x addr -- ) | Store x at addr                               |
| `sp@`     | ( -- sp )     | Get pointer to top of data stack              |
| `rp@`     | ( -- rp )     | Get pointer to top of return stack            |
| `0=`      | ( x -- flag ) | -1 if top of stack is 0, 0 otherwise          |
| `+`       | ( x y -- z )  | Sum the two numbers at the top of the stack   |
| `nand`    | ( x y -- z )  | NAND the two numbers at the top of the stack  |
| `exit`    | ( r:addr -- ) | Pop return stack and resume execution at addr |
| `key`     | ( -- x )      | Read key stroke as ASCII character            |
| `emit`    | ( x -- )      | Print low byte of x as an ASCII character     |
| `boot`    | ( -- )        | Replace input with source from disk CHS 0/0/2 |

### Variables

| Variable | Description                                                   |
| -------- | ------------------------------------------------------------- |
| `state`  | 0: execute words; 1: compile word addresses to the dictionary |
| `tib`    | Terminal input buffer, where input is parsed from             |
| `>in`    | Current parsing offset into terminal input buffer             |
| `here`   | Pointer to next free position in the dictionary               |
| `latest` | Pointer to most recent dictionary entry                       |

## Compiling

sectorforth was developed using NASM 2.15.01. Earlier versions of NASM
are probably capable of compiling it, but that hasn't been tested.

Building requires NASM, Make, and Python 3. To compile sectorforth, run `make`:

```
$ make
```

That will produce a compiled binary (`sectorforth.bin`) and a floppy disk
image (`sectorforth.img`) containing the binary in its boot sector.
The image is a 360 KB floppy with `bootstrap.f` packed into its second
sector, followed by the numbered files in `forth/`. The boot sector remains
exactly 512 bytes; the rest of the system arrives as interpreted ASCII
source.

To append further source files after the workbench, list them in disk order:

```
make EXTRA_SOURCES="next.f more.f"
```

Pass the same list to `run`, `gdb`, or `test`, since those targets rebuild
the image, for example `make run EXTRA_SOURCES="next.f more.f"`. The builder
prints both physical sector numbers and zero-based logical addresses.
`SOURCE_SECTORS` can still override the complete source list for a custom
bootstrap; the default numbered files must retain their order.

Each file occupies one 512-byte sector. The builder converts whitespace
to spaces, permits at most 510 source bytes after that conversion, and
adds space padding plus a final space/NUL terminator. It rejects oversized
or non-ASCII source rather than splitting definitions across sectors.
It does not remove comments or understand quoted strings: use plain,
space-delimited Forth source that the current dictionary can interpret.
The commented files in `examples/` need preparation before packing.

Logical sectors 0–63 are reserved for the rebuildable boot and source
area. The workbench stores its blocks from logical sector 64 onward.
Rebuilding preserves that data area, and `make clean` keeps the image.
`make fresh-image` explicitly discards saved blocks and creates a fresh
image. Do not rebuild an image while QEMU is using it.

An existing 1.44 MB image is converted to 360 KB only if the discarded
region is entirely zero-filled. Saved blocks within the new capacity are
preserved. If occupied blocks lie beyond that capacity, rebuilding stops
without changing the image so those blocks can be migrated first.

## Running

The makefile contains two targets for running sectorforth in QEMU:

- `gdb` starts QEMU in debug mode, with execution paused. That allows
you to set up a remote target in GDB (`target remote localhost:1234`) and
set any breakpoints you want before sectorforth starts running.
- `run` simply runs sectorforth in QEMU.

Both targets boot the complete image as a floppy. QEMU is required for
these targets and for `make test`, which checks image packing and exercises
the BIOS disk reader, keyboard input, and source chaining in headless QEMU.
The QEMU regression guest uses a 486 CPU model and 16 MB because its
bundled SeaBIOS does not boot with 512 KB. The 8088 instruction set is
enforced by NASM; QEMU does not certify actual XT timing or BIOS behavior.
See [the XT platform notes](docs/xt-platform.md) for the compatibility
changes and validation limits.

## Usage

After reset, the first-sector interpreter waits on a blank line with no
readiness prompt. Click the QEMU display and enter lowercase `boot` once.
It should echo there; the terminal running Make is not the guest keyboard.
The default source chain has no progress display and took about 41 seconds
in a local QEMU startup before displaying `sf> `. Wait for that prompt
before entering more commands. The workbench accepts up to 4,094 characters
per line, recognizes decimal integers, and compiles numeric literals:

```forth
: answer 40 2 + ;
answer .
```

This prints `42`. Names remain case-sensitive. Backspace edits the current
screen row; the block line editor stays within one row.

Errors print `!!` in red and return to the first-sector input loop.
Enter `workbench` to resume the richer prompt. Completed dictionary
entries and dirty block data remain in RAM; the data and return stacks
and evaluation depth are reset. Reset the machine to repeat the complete
bootstrap rather than replaying it into the existing dictionary.

Invalid executable addresses and arbitrary memory corruption are still
outside the interpreter's error handling.

The first-sector input routine itself still ignores Backspace. Its minimal
behavior makes room for disk access; editing and numeric interpretation
are supplied by the loaded Forth source.

## Bootstrapping from source

The default bootstrap installs these loading interfaces:

| Word | Stack effects | Behavior |
| --- | --- | --- |
| `sector-load` | `( sector -- )` | Replace current input with one logical source sector. |
| `next-source` | `( -- )` | Continue from the next logical sector of disk source being interpreted. |
| `load-chs` | `( cylinder head sector -- )` | Source replacement using BIOS CHS coordinates. |
| `evaluate` | `( address length -- )` | Interpret memory, then restore caller input and resume. |
| `sector-evaluate` | `( sector -- )` | Interpret a source sector and return to the caller. |
| `sector-thru` | `( first last -- )` | Interpret an inclusive logical-sector range in order. |

Logical sector 0 is the boot sector, 1 contains `bootstrap.f`, and 2 starts
the numbered foundation files. Source loaders reject sector 0. Appended
source files currently start at logical sector 27; use the builder's output
for the address if the core source count changes. For example, a file at
sector 27 can be invoked with `27 sector-evaluate`. It can end with
`next-source` to continue into the following file without embedding its
address. `next-source` requires a disk-source context, not an arbitrary
memory string or keyboard command.

Returning evaluation preserves the caller's input and stack results and
supports four active evaluation frames. The interactive command itself
uses one frame. The maximum evaluated region is 4,094 bytes. See
[the source implementation notes](forth/README.md) for the reserved RAM
layout and remaining compatibility limits.

## Disk workbench

The workbench supplies `block`, `buffer`, `list`, returning `load`, `thru`,
`update`, `save-buffers`, `flush`, `blank-block`, and `edit-line`.
Block numbers 1–328 each address 1,024 bytes, starting at logical sector
64. `load` now takes one block number; the original CHS operation has the
distinct name `load-chs`.

To write and run a small source block, enter:

```forth
1 blank-block
0 1 edit-line
```

At `edit> `, type `123 456 + .` and press Enter. Then enter:

```forth
save-buffers
flush
1 list
1 load
```

`list` displays the source without executing it; `load` prints `579`.
The editor replaces a numbered line (0–15), with at most 64 characters.
There is one block buffer: changing blocks saves dirty contents before
reuse. `save-buffers` writes changes explicitly, and `flush` also drops the
cached block. Saved blocks survive QEMU restarts and image rebuilds.
There is no filesystem or full-screen editor yet.

The [minimal loader history](docs/history/minimal-loader.md) records the
earlier CHS-only environment and its source-replacement behavior.

The [development roadmap](ROADMAP.md) prioritizes logical loading,
sequential source continuation, returning evaluation, and a disk workbench,
then builds toward a more standard Forth dictionary and interpreter.

## Code structure

Comments throughout the code assume familiarity with Forth and how it is
commonly implemented.

If you're not familiar with Forth, read Leo Brodie's
[Starting Forth](https://www.forth.com/starting-forth).

If you're not familiar with how Forth is implemented on x86, read the
assembly code for Richard W.M. Jones'
[jonesforth](http://git.annexia.org/?p=jonesforth.git;a=blob;f=jonesforth.S).

sectorforth draws a lot of inspiration from jonesforth, but the latter
does a much better job at explaining the basics in its comments.

For an excellent introduction to threaded code techniques, and to how to
implement Forth in different architectures, read Brad Rodriguez's
[Moving Forth](http://www.bradrodriguez.com/papers/moving1.htm).
