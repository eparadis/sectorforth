name = sectorforth
PYTHON ?= python3
SOURCE_SECTORS ?= bootstrap.f

all: $(name).bin $(name).img

%.bin: %.asm
	nasm -f bin -o $@ -l $(^:.asm=.lst) $^

$(name).img: $(name).bin tools/build_image.py $(SOURCE_SECTORS) FORCE
	$(PYTHON) tools/build_image.py $(name).bin $@ $(SOURCE_SECTORS)

.PHONY: all gdb run clean test FORCE
gdb: $(name).img
	qemu-system-i386 -drive file=$<,format=raw,if=floppy -boot a -monitor stdio -s -S

run: $(name).img
	qemu-system-i386 -drive file=$<,format=raw,if=floppy -boot a

clean:
	rm -f $(name).bin $(name).lst $(name).img

test: all
	$(PYTHON) tests/test_boot.py

# The source-file list can change without any file timestamps changing.
FORCE:
