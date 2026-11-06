# Roadmap toward a standalone Forth environment

Grow sectorforth into a useful interactive Forth on real hardware while
retaining a complete 512-byte starting environment. The first sector
supplies the interpreter, compiler, primitives, and enough disk access to
interpret further Forth source. Higher-level capabilities continue to
arrive as text, rather than requiring a binary second-stage kernel.

The first major goal is a Forth-written interpreter with arbitrary numeric
input, literal compilation, editable input, and useful diagnostics. Standard
compatibility can then be expanded and checked against the
[Forth standard](https://forth-standard.org/standard/core).

## Current starting environment

The kernel assembled from [sectorforth.asm](sectorforth.asm) occupies
exactly 512 bytes, including the boot signature. It retains the original
computational primitives and colon compiler, adds `boot`, and ignores Backspace to make room for disk
access. The implementation uses 16-bit cells and requires a 386 or newer
CPU with BIOS services.

Typing `boot` interprets the second physical sector of the boot disk.
[bootstrap.f](bootstrap.f) currently uses 498 of the available 510 source
bytes. It defines numeric constants `0` through `10`, basic stack and
logic operations, and `load ( cylinder head sector -- )`. This loader
replaces the current input buffer; a final load command can continue from
another source sector. It does not preserve and resume an earlier source.

The image builder packs one source file per sector, folds whitespace to
spaces, and supplies padding and a space/NUL terminator. The default image
contains the boot sector and bootstrap source, with the remaining sectors
zero-filled. See [the README](README.md#bootstrapping-from-source) for
current build and loading instructions.

## Proposed implementation stages

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

Implement stages 1 through 3 first. Conditionals, loops, and literal
compilation make a numeric parser much easier to write; the existing
numeric constants can carry the bootstrap until then.

Split these definitions into source files that load in dependency order.
Keep each definition within a sector and reserve space for the command
that loads the next one. Continue using the current CHS loader until the
new input system can support a richer loading interface.

Verify the new foundation in QEMU with stack-effect checks, both branches
of conditionals, terminating loops, balanced return-stack operations, and
definitions compiled across successive source sectors. Retain the existing
disk-loading and error-recovery checks. Exercise arithmetic boundary cases
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
