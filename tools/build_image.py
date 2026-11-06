#!/usr/bin/env python3
"""Pack a boot sector and ASCII Forth source sectors into an XT 360 KB floppy."""

import argparse
from pathlib import Path

SECTOR_SIZE = 512
CYLINDERS = 40
HEADS = 2
SECTORS_PER_TRACK = 9
FLOPPY_SECTORS = CYLINDERS * HEADS * SECTORS_PER_TRACK
SOURCE_LIMIT = SECTOR_SIZE - 2
WORKBENCH_START = 64
WORKBENCH_BLOCKS = (FLOPPY_SECTORS - WORKBENCH_START) // 2
LEGACY_IMAGE_SIZE = 2880 * SECTOR_SIZE


def source_sector(path):
    raw = path.read_bytes()
    if b"\0" in raw:
        raise ValueError(f"{path}: source must not contain NUL bytes")
    text = raw.decode("ascii")
    if any(ord(c) < 32 and c not in "\t\r\n" for c in text) or "\x7f" in text:
        raise ValueError(f"{path}: source contains unsupported control characters")
    # The minimal interpreter only splits tokens at ASCII spaces. This is
    # token-oriented source, with no comment or quoted-string preprocessing.
    source = " ".join(text.split()).encode("ascii")
    if len(source) > SOURCE_LIMIT:
        raise ValueError(f"{path}: {len(source)} source bytes exceed the {SOURCE_LIMIT}-byte limit")
    return source.ljust(SOURCE_LIMIT, b" ") + b" \0", len(source)


def build_image(boot_path, source_paths, previous=None):
    boot = boot_path.read_bytes()
    if len(boot) != SECTOR_SIZE or boot[510:] != b"\x55\xaa":
        raise ValueError(f"{boot_path}: expected a 512-byte boot sector ending in 55 aa")
    if len(source_paths) >= WORKBENCH_START:
        raise ValueError("source sectors overlap the workbench data area at LBA 64")
    image_size = SECTOR_SIZE * FLOPPY_SECTORS
    if previous is not None and len(previous) == LEGACY_IMAGE_SIZE:
        # The old 1.44 MB layout used the same data-area start. Preserve
        # every block that fits, but never silently discard occupied blocks.
        if any(previous[image_size:]):
            raise ValueError("existing 1.44 MB image has data beyond the 360 KB capacity; "
                             "migrate those blocks before rebuilding (the image was not changed)")
        previous = previous[:image_size]
    if previous is not None and len(previous) != image_size:
        raise ValueError("existing image has the wrong size; use --fresh to replace it")
    image = bytearray(previous) if previous is not None else bytearray(image_size)
    image[:WORKBENCH_START * SECTOR_SIZE] = bytes(WORKBENCH_START * SECTOR_SIZE)
    image[:SECTOR_SIZE] = boot
    sizes = []
    for index, path in enumerate(source_paths, start=1):
        sector, used = source_sector(path)
        image[index * SECTOR_SIZE:(index + 1) * SECTOR_SIZE] = sector
        sizes.append(used)
    return image, sizes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("boot", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("sources", nargs="+", type=Path,
                        help="one source file per sector, starting at physical sector 2")
    parser.add_argument("--fresh", action="store_true",
                        help="discard any existing image, including saved workbench blocks")
    args = parser.parse_args()
    try:
        previous = args.output.read_bytes() if args.output.exists() and not args.fresh else None
        image, sizes = build_image(args.boot, args.sources, previous)
        args.output.write_bytes(image)
    except (OSError, UnicodeError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    for number, (path, used) in enumerate(zip(args.sources, sizes), start=2):
        print(f"sector {number} (LBA {number - 1}): {path} ({used}/{SOURCE_LIMIT} source bytes)")


if __name__ == "__main__":
    main()
