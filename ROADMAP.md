# Roadmap toward a standalone Forth environment

Grow sectorforth into a useful interactive Forth on real hardware while
retaining a complete 512-byte starting environment. The first sector
supplies the interpreter, compiler, primitives, and enough disk access to
interpret further Forth source. Higher-level capabilities continue to
arrive as text, rather than requiring a binary second-stage kernel.

The immediate goal is to make loading the rest of the system simpler:
logical sector addressing, sequential continuation, returning source
evaluation, and a small disk workbench. A Forth-written interpreter with
arbitrary numeric input, literal compilation, editable input, and useful
diagnostics follows. Standard compatibility can then be checked against the
[Forth standard](https://forth-standard.org/standard/core).

## Current starting environment

The kernel assembled from [sectorforth.asm](sectorforth.asm) occupies
exactly 512 bytes, including the boot signature. It retains the original
computational primitives and colon compiler, adds `boot`, and ignores
Backspace to make room for disk access. The implementation uses 16-bit cells and requires a 386 or newer
CPU with BIOS services.

Typing `boot` interprets the second physical sector of the boot disk.
[bootstrap.f](bootstrap.f) currently uses 509 of the available 510 source
bytes. It defines the initial numeric constants, stack and logic operations,
and a CHS source loader, then continues into the numbered files in
[forth/](forth/README.md). That source chain installs logical loading,
returning evaluation, decimal numeric input, and a small disk workbench.
The original replacement loader remains available as `load-chs`; the final
`load` interprets a 1,024-byte block and resumes its caller.

The image builder packs one source file per sector, folds whitespace to
spaces, and supplies padding and a space/NUL terminator. The default image
contains the boot sector, bootstrap, and numbered workbench source files.
Logical sectors 64 onward hold saved workbench data and are preserved when
the image is rebuilt. See [the README](README.md#bootstrapping-from-source)
for current build and loading instructions, and
[the minimal loader history](docs/history/minimal-loader.md) for the
earlier CHS-only implementation.

## Loading infrastructure first

Build the small foundation needed by the loader before expanding the full
language. Keep the first sector complete and put these additions in loaded
Forth source. Initial implementations of phases A through D and a minimal
phase E now exist: one block buffer, explicit saves, listing, and line
replacement. The broader compatibility and editing work remains below.

| Phase | Interfaces and machinery | Result |
| --- | --- | --- |
| A. Minimal foundation | Only the stack, memory, literal, branch, and storage helpers needed below | Enough machinery for address conversion, source state, and bounded loops. |
| B. Logical and sequential loading | Preserve `load-chs`; add `sector-load ( sector -- )`, current-source tracking, and `next-source ( -- )` | Source files stop embedding CHS coordinates and their successors' physical addresses. |
| C. Returning source evaluation | Bounded interpretation of a memory region; saved input and execution state; `EVALUATE` | A caller resumes after the loaded source finishes; nested evaluation becomes possible. |
| D. Readable disk workbench | Separate raw sector reads from interpretation; add source inspection and returning sector/range loading | Modules can load other modules, ranges interpret every member, and disk contents can be inspected without executing them. |
| E. Writable disk workbench | Disk writes, buffers, explicit saves, then a source editor | The user can develop and preserve source directly on the machine. |

Use zero-based logical disk sectors: sector 0 contains the boot code,
sector 1 contains `bootstrap.f`, and sector 2 contains the next source.
Source-loading interfaces must reject sector 0. Keep BIOS CHS conversion
underneath those interfaces and distinguish these 512-byte sectors from
future standard 1,024-character blocks.

`NEXT-SOURCE` initially replaces the current input, just like the existing
loader. It tracks the current logical source sector and advances it before
loading. Each bootstrap source can end with the same continuation command;
moving a group of sectors then changes its starting address rather than
every link in the chain.

Do not implement a range loader by repeatedly calling the current `load`
inside a loop. That word returns before the replacement text is interpreted,
so subsequent reads overwrite source that has not run. A range needs
returning evaluation, a refill mechanism, or a combined source buffer.
Phase C establishes returning evaluation before phase D exposes that
interface.

Raw reads should eventually take a logical sector and destination address
and return an I/O result, without changing the input source. The current
reader fixes its destination and resets the interpreter on failure; this
separation requires implementation work, not just a new name.

## Later language expansion stages

These stages describe dependencies and useful capabilities, not fixed
sector assignments. A stage can span several source sectors.

| Stage | Vocabulary and facilities | Result |
| --- | --- | --- |
| 1. Basic operations | `DROP NIP TUCK 2DUP 2DROP INVERT OR XOR NEGATE - = <> 1+ 1-` | Ordinary stack manipulation, logic, and arithmetic expressions. |
| 2. Memory and compiler foundation | `C@ C! , C, CELLS CELL+ +! IMMEDIATE [ ]`, internal literal and branch helpers | Byte access, dictionary construction, and words that control compilation. |
| 3. Control structures and return stack | `IF ELSE THEN BEGIN UNTIL AGAIN WHILE REPEAT`, `>R R> R@ ROT`, then counted loops such as `DO LOOP I` | Practical algorithms and the machinery for later parsers and compiler extensions. |
| 4. Defining words | `CREATE ALLOT VARIABLE CONSTANT`, followed by `DOES>` | Named storage, tables, configuration, and custom data structures. |
| 5. Arithmetic and numeric I/O | Signed and unsigned comparisons, `* /MOD / MOD`, `BASE DECIMAL HEX . U.`, and `.S` | Useful calculations, numeric conversion, and stack inspection. |
| 6. Parsing and text | `BL SPACE CR TYPE PARSE PARSE-NAME CHAR [CHAR]`, comments, and string literals | Readable source, messages, and command parsing. |
| 7. Forth interpreter | `FIND EXECUTE ' ['] LITERAL POSTPONE ACCEPT REFILL QUIT ABORT EVALUATE`, with numeric conversion | A familiar interactive session with numbers, compilation, editing, and error recovery. |
| 8. Disk workbench | Buffered disk access, `BLOCK BUFFER LIST LOAD THRU`, then `UPDATE SAVE-BUFFERS FLUSH` and a source editor | Viewing, loading, editing, and saving source on the machine itself. |

Numeric conversion can begin with an internal single-cell conversion
routine. Standard words such as `>NUMBER`, and full Core coverage, require
their specified interfaces and any supporting double-cell arithmetic.

## Next implementation milestone

Use the loading infrastructure to carry the broader language stages above.
The current implementation already adds the helpers required by the
loaders and a decimal interpreter; extend those definitions toward standard
semantics rather than installing parallel copies of the original examples.
Validate the disk bridge on real hardware, add a disk retry policy, and
improve recovery into the Forth input loop before treating the workbench as
a finished standalone development system.

Split these definitions into source files that load in dependency order.
Keep each definition within a sector and reserve space for its continuation
command. Use explicit CHS continuation only to establish logical loading;
subsequent bootstrap sectors should use `NEXT-SOURCE`.

Verify logical addressing across track and cylinder boundaries, sequential
continuation after relocation, and rejection of invalid source addresses.
Returning evaluation must preserve caller input, stack results, and
execution order, including nested loads and definitions compiled from
source. Inspection must not execute the inspected source. Retain disk-error
recovery checks and add a save/reload test before enabling writes.

Verify new language helpers with stack-effect checks, both branches of
conditionals, terminating loops, and balanced return-stack operations.
Exercise arithmetic boundary cases
when comparisons and division are added; subtraction followed by a sign
test alone does not correctly implement every signed comparison.

Useful starting points already exist:

- [01-helloworld.f](examples/01-helloworld.f) develops compiler helpers,
  control structures, return-stack operations, and strings.
- [03-variables.f](examples/03-variables.f) explores creation and allocation.
- [04-debugstack.f](examples/04-debugstack.f) adds division, numeric output,
  and stack inspection.

Adapt and test those definitions rather than treating their names as proof
of standard semantics. Their comments and stack annotations also need
preparation before the current interpreter can consume them.

## Interpreter and compatibility transitions

### Take over the input loop

A number-conversion word cannot change the assembly interpreter's behavior
by itself. The later Forth interpreter must parse a token, search the
dictionary, and, if lookup fails, attempt numeric conversion. In
interpretation state it executes words or leaves numbers on the stack; in
compilation state it handles immediate words and compiles word references
or numeric literals. A Forth-written `QUIT` should own input and recovery.
See the [text interpreter requirements](https://forth-standard.org/standard/usage)
and [QUIT](https://forth-standard.org/standard/core/QUIT).

An initial input routine can restore line editing using the existing
keyboard and display facilities. Restoring the original cross-row
backspace behavior may require additional cursor support. Loading a word
named Backspace does not replace the assembly input loop.

### Adapt bootstrap names and interfaces

The bootstrap environment exposes implementation details that later
standard interfaces should wrap or replace:

- Current `here` returns the address of the dictionary pointer variable;
  standard [HERE](https://forth-standard.org/standard/core/HERE) returns the
  allocation pointer itself. Preserve access to the underlying variable
  for implementation code when introducing the standard interface.
- Current `key` returns BIOS scan-code information along with the ASCII
  byte. Standard [KEY](https://forth-standard.org/standard/core/KEY) returns
  a character and discards keyboard events that are not characters.
- The named constant `10` shadows numeric interpretation. In hexadecimal
  mode it would still execute the decimal-ten word. Hide or retire the
  bootstrap numeral names when installing numeric parsing, while retaining
  the definitions referenced by already-compiled words.
- The example named `[']` is an internal inline-literal reader. The standard
  [bracket-tick word](https://forth-standard.org/standard/core/BracketTick)
  parses a name during compilation and compiles its execution token. Give
  the internal helper a distinct name before supplying the standard word.
- Preserve the current CHS loader under a distinct name before introducing
  standard block-oriented `LOAD`.

Add standard interfaces alongside the implementation machinery so the
bootstrap can still complete while the new environment is being built.

### Preserve source text when parsing grows

The current image builder folds all whitespace and does not parse comments
or quoted strings. Line comments require preserved line boundaries or a
defined preprocessing step. Strings require preserving significant spaces.
Update the packing policy together with the parser, rather than silently
changing source text that the new environment expects to interpret.

The initial 510-byte source limit is a transport format, not a permanent
limit on the interpreter. A later source system can use larger buffers and
multiple sectors. The compiled dictionary and stacks still share the
current single 64 KB memory segment, so track their RAM use separately from
packed source size.

## Standalone disk workbench

A traditional block-oriented workbench is a practical destination for the
floppy-based system. Standard Forth blocks contain 1,024 characters, so
each block can occupy two physical floppy sectors. Buffered block access
and an editor would let the user change and save Forth source directly on
the machine. This requires a disk-write path in addition to the existing
reader.

Standard `LOAD` saves and restores the previous input source, allowing
nested loads. That requires input-source state and buffer management beyond
the current replacement loader. Add `LIST` and loading first, then dirty
buffer tracking, explicit saves, and editing. See the
[Block word set](https://forth-standard.org/standard/block).

Keep QEMU checks for each bootstrap milestone and add real-hardware
validation as the disk and console interfaces grow. Expand standard
coverage by checking stack effects and behavior, rather than word names
alone. A useful subset can serve the machine before full conformance is
reached.
