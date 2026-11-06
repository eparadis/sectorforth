name = sectorforth
PYTHON ?= python3
QEMU ?= qemu-system-i386
# QEMU's oldest CPU model is a 486. SeaBIOS gets 16 MB for regression
# testing; the actual minimum target is an 8088 XT with 512 KB of RAM.
QEMU_ARGS ?= -machine pc -cpu 486 -m 16M
SOURCE_SECTORS ?= bootstrap.f $(sort $(wildcard forth/*.f)) $(EXTRA_SOURCES)

all: $(name).bin $(name).img

%.bin: %.asm
	nasm -f bin -o $@ -l $(^:.asm=.lst) $^

$(name).img: $(name).bin tools/build_image.py $(SOURCE_SECTORS) FORCE
	$(PYTHON) tools/build_image.py $(name).bin $@ $(SOURCE_SECTORS)

.PHONY: all gdb run clean fresh-image test FORCE
gdb: $(name).img
	$(QEMU) $(QEMU_ARGS) -drive file=$<,format=raw,if=floppy -boot a -monitor stdio -s -S

run: $(name).img
	$(QEMU) $(QEMU_ARGS) -drive file=$<,format=raw,if=floppy -boot a

clean:
	rm -f $(name).bin $(name).lst

fresh-image: $(name).bin
	$(PYTHON) tools/build_image.py --fresh $(name).bin $(name).img $(SOURCE_SECTORS)

test: all
	$(PYTHON) tests/test_boot.py $(TEST_ARGS)

# The source-file list can change without any file timestamps changing.
FORCE:
