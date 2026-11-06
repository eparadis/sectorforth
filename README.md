# sectorforth

sectorforth is a 16-bit x86 Forth that fits in a 512-byte boot sector.

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

Contrary to many Forth implementations, sectorforth does not attempt to
convert unknown words to numbers, since numbers can be produced using the
available primitives. The two included I/O primitives are sufficient to
write a more powerful interpreter that can parse numbers.

Typing `boot` loads the second sector of the boot disk as Forth source.
The included [bootstrap.f](bootstrap.f) builds numeric constants and a
CHS-addressed source loader, so additional source sectors can extend the
dictionary without loading binary instructions from disk.

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
The image is a 1.44 MB floppy with `bootstrap.f` packed into its second
sector. The boot sector remains exactly 512 bytes; later sectors contain
ASCII source interpreted by that first-sector implementation.

To include further source files, list them in disk order:

```
make SOURCE_SECTORS="bootstrap.f next.f more.f"
```

Pass the same list to `run`, `gdb`, or `test`, since those targets rebuild
the image, for example `make run SOURCE_SECTORS="bootstrap.f next.f more.f"`.

Each file occupies one 512-byte sector. The builder converts whitespace
to spaces, permits at most 510 source bytes after that conversion, and
adds space padding plus a final space/NUL terminator. It rejects oversized
or non-ASCII source rather than splitting definitions across sectors.
It does not remove comments or understand quoted strings: use plain,
space-delimited Forth source that the current dictionary can interpret.
The commented files in `examples/` need preparation before packing.

## Running

The makefile contains two targets for running sectorforth in QEMU:

- `gdb` starts QEMU in debug mode, with execution paused. That allows
you to set up a remote target in GDB (`target remote localhost:1234`) and
set any breakpoints you want before sectorforth starts running.
- `run` simply runs sectorforth in QEMU.

Both targets boot the complete image as a floppy. QEMU is required for
these targets and for `make test`, which checks image packing and exercises
the BIOS disk reader, keyboard input, and source chaining in headless QEMU.

## Usage

Up to 4KB of input can be entered per line. After pressing return, the
interpreter parses one word at a time an interprets it (i.e. executes it
or compiles it, according to the current value of the `state` variable).

sectorforth does not print the ` ok` prompt familiar to Forth users.
However, if a word is not found in the dictionary, the error message `!!`
is printed in red, letting you know an error happened.

When a word is not found in the dictionary, the interpreter's state is
reset: the data and return stacks, as well as the terminal input buffer
are cleared, and the interpreter is placed in interpretation mode. Other
errors (e.g. compiling an invalid address in a word definition and
attempting to execute it) are not handled gracefully, and will crash the
interpreter.

The first-sector input routine ignores Backspace. Character echo, Enter,
and newlines are supported; editing can be supplied by a later Forth input
loop. This simplification makes room for the disk reader while retaining
the original computational primitives and compiler.

## Bootstrapping from source

After starting the machine, enter:

```forth
boot
```

This silently interprets `bootstrap.f` and returns to keyboard input. It
defines constants `0` through `10`, `dup`, `over`, `swap`, `and`, `2*`,
`256*`, `ff` (255), and:

```forth
load ( cylinder head sector -- )
```

The stack annotation above is documentation, not text to type. With an
image built using `bootstrap.f next.f more.f`, load `next.f` with:

```forth
0 0 3 load
```

That source can end with `0 0 4 load` to interpret `more.f`, continuing the
bootstrap. Completed definitions remain in RAM across loads.

Addresses use BIOS cylinder/head/sector coordinates, with a one-based
sector number. For the 1.44 MB image, cylinders are 0–79, heads 0–1, and
sectors 1–18. Physical sector 19 is `0 1 1 load`; physical sector 37 is
`1 0 1 load`. There is no filesystem or general decimal-number parser yet:
`0` through `10` are named constant words. Construct larger values using
arithmetic, for example `0 0 9 2* load` for sector 18 on the first track.

`boot` and `load` replace the current input buffer; any remaining text in
that buffer is discarded. They do not save and resume a previous source
like a nested standard Forth `LOAD`. Use loads in interpretation state,
after completing any definitions. When a sector's source ends, keyboard
input resumes. Disk errors print `!!` and reset the stacks and input,
retaining completed dictionary entries and restoring `boot` to CHS 0/0/2.
There are no automatic disk retries.

The bootstrap loader is Forth source. It temporarily patches the native
reader's CHS operands using `@` and `!`, calls `boot`, and restores its
fixed address afterward. `(load)` and `(reset)` are internal helpers;
the assembler checks their required operand offsets. The BIOS boot-drive
number is retained, rather than assuming drive A:.

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
