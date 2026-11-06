#!/usr/bin/env python3
"""Image-format checks and a real BIOS/keyboard/Forth integration test in QEMU."""

import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_image", ROOT / "tools/build_image.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class ImageTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "tmp").mkdir(exist_ok=True)
        self.work = tempfile.TemporaryDirectory(prefix="image-", dir=ROOT / "tmp")
        self.addCleanup(self.work.cleanup)
        self.path = Path(self.work.name) / "source.f"

    def test_bootstrap_and_image_layout(self):
        image, sizes = builder.build_image(ROOT / "sectorforth.bin", [ROOT / "bootstrap.f"])
        self.assertEqual(len(image), 368640)
        self.assertEqual(builder.WORKBENCH_BLOCKS, 328)
        self.assertEqual(image[:512], (ROOT / "sectorforth.bin").read_bytes())
        self.assertEqual(image[510:512], b"\x55\xaa")
        self.assertEqual(image[1022:1024], b" \0")
        self.assertLessEqual(sizes[0], 510)
        self.assertNotIn(b"\0", image[512:1023])
        self.assertEqual(image[1024:], bytes(len(image) - 1024))

    def test_whitespace_and_size_limit(self):
        self.path.write_bytes(b":\tword\r\nkey emit ;\n")
        sector, used = builder.source_sector(self.path)
        self.assertEqual(sector[:used], b": word key emit ;")
        self.assertEqual(len(sector), 512)
        self.path.write_bytes(b"x" * 510)
        self.assertEqual(builder.source_sector(self.path)[0][-2:], b" \0")
        self.path.write_bytes(b"x" * 511)
        with self.assertRaisesRegex(ValueError, "510-byte limit"):
            builder.source_sector(self.path)

    def test_reject_invalid_inputs(self):
        for data in (b"bad\0source", b"bad\x08source", b"\xff"):
            self.path.write_bytes(data)
            with self.assertRaises((ValueError, UnicodeError)):
                builder.source_sector(self.path)
        self.path.write_bytes(bytes(512))
        with self.assertRaisesRegex(ValueError, "boot sector"):
            builder.build_image(self.path, [ROOT / "bootstrap.f"])

    def test_rebuild_preserves_saved_blocks(self):
        image, _ = builder.build_image(ROOT / "sectorforth.bin", [ROOT / "bootstrap.f"])
        start = builder.WORKBENCH_START * 512
        image[start:start + 6] = b"saved!"
        image[32 * 512:32 * 512 + 3] = b"old"
        path = Path(self.work.name) / "saved.img"
        path.write_bytes(image)
        command = [sys.executable, str(ROOT / "tools/build_image.py"),
                   str(ROOT / "sectorforth.bin"), str(path), str(ROOT / "bootstrap.f")]
        subprocess.run(command, check=True, capture_output=True)
        rebuilt = path.read_bytes()
        self.assertEqual(rebuilt[start:], image[start:])
        self.assertEqual(rebuilt[1024:start], bytes(start - 1024))
        subprocess.run(command + ["--fresh"], check=True, capture_output=True)
        self.assertEqual(path.read_bytes()[start:], bytes(len(image) - start))

    def test_reserved_workbench_area(self):
        with self.assertRaisesRegex(ValueError, "overlap"):
            builder.build_image(ROOT / "sectorforth.bin", [ROOT / "bootstrap.f"] * 64)
        with self.assertRaisesRegex(ValueError, "wrong size"):
            builder.build_image(ROOT / "sectorforth.bin", [ROOT / "bootstrap.f"], b"bad")

    def test_legacy_image_migration(self):
        previous = bytearray(builder.LEGACY_IMAGE_SIZE)
        start = builder.WORKBENCH_START * 512
        previous[start:start + 6] = b"saved!"
        image, _ = builder.build_image(ROOT / "sectorforth.bin", [ROOT / "bootstrap.f"], previous)
        self.assertEqual(len(image), 368640)
        self.assertEqual(image[start:], previous[start:len(image)])
        previous[-1] = 1
        with self.assertRaisesRegex(ValueError, "migrate those blocks"):
            builder.build_image(ROOT / "sectorforth.bin", [ROOT / "bootstrap.f"], previous)
        # CLI failure must leave the original image byte-for-byte intact.
        path = Path(self.work.name) / "old.img"
        path.write_bytes(previous)
        result = subprocess.run([sys.executable, str(ROOT / "tools/build_image.py"),
                                 str(ROOT / "sectorforth.bin"), str(path), str(ROOT / "bootstrap.f")],
                                capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(path.read_bytes(), previous)


class Qemu:
    def __init__(self, work, image, readonly=True, cpu="486", memory="16M"):
        self.work = work
        self.sequence = 0
        self.qmp = None
        self.log = (work / "qemu.log").open("w+")
        self.process = subprocess.Popen([
            "qemu-system-i386", "-machine", "pc", "-cpu", cpu, "-m", memory,
            "-drive", f"file={image},format=raw,if=floppy,readonly={'on' if readonly else 'off'}",
            "-boot", "a", "-display", "none", "-monitor", "none", "-serial", "none",
            "-qmp", f"unix:{work / 'qmp'},server=on,wait=off",
            "-no-reboot",
        ], stdout=self.log, stderr=self.log)
        try:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if self.process.poll() is not None:
                    self.log.seek(0)
                    raise RuntimeError(f"QEMU exited: {self.log.read()}")
                connection = socket.socket(socket.AF_UNIX)
                try:
                    connection.connect(str(work / "qmp"))
                except OSError:
                    connection.close()
                    time.sleep(0.05)
                    continue
                self.qmp = connection
                self.qmp.settimeout(10)
                self.stream = connection.makefile("rb")
                json.loads(self.stream.readline())
                self.command("qmp_capabilities")
                return
            raise TimeoutError("QEMU did not open QMP")
        except BaseException:
            self.close()
            raise

    def command(self, name, arguments=None):
        self.sequence += 1
        request = {"execute": name, "id": self.sequence}
        if arguments is not None:
            request["arguments"] = arguments
        self.qmp.sendall(json.dumps(request).encode() + b"\n")
        while True:
            line = self.stream.readline()
            if not line:
                raise RuntimeError("QEMU closed QMP")
            response = json.loads(line)
            if response.get("id") == self.sequence:
                if "error" in response:
                    raise RuntimeError(response["error"])
                return response["return"]

    def monitor(self, text):
        return self.command("human-monitor-command", {"command-line": text})

    def type(self, text):
        names = {" ": "spc", "\n": "ret", "\b": "backspace", ".": "dot",
                 ":": "shift-semicolon", ";": "semicolon", "+": "shift-equal",
                 "-": "minus", "@": "shift-2", "!": "shift-1", "<": "shift-comma",
                 "=": "equal",
                 ">": "shift-dot", "/": "slash", "?": "shift-slash",
                 "[": "bracket_left", "]": "bracket_right", "'": "apostrophe"}
        for char in text:
            result = self.monitor(f"sendkey {names.get(char, char)} 10")
            if result:
                raise RuntimeError(result)
            time.sleep(0.035)

    def screen(self):
        path = self.work / "vga.bin"
        result = self.monitor(f'pmemsave 0xb8000 4000 "{path}"')
        if result:
            raise RuntimeError(result)
        chars = path.read_bytes()[::2]
        return "\n".join(chars[i:i + 80].decode("cp437").replace("\0", " ") for i in range(0, 2000, 80))

    def memory(self, address, count):
        path = self.work / "memory.bin"
        result = self.monitor(f'pmemsave {address} {count} "{path}"')
        if result:
            raise RuntimeError(result)
        return path.read_bytes()

    def wait_for(self, text, timeout=10):
        deadline = time.monotonic() + timeout
        screen = ""
        while time.monotonic() < deadline:
            screen = self.screen()
            if text in screen:
                return screen
            time.sleep(0.05)
        raise AssertionError(f"screen never contained {text!r}:\n{screen}")

    def prompt_after(self, output, timeout=30):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            screen = self.screen()
            lines = screen.splitlines()
            for index, line in enumerate(lines):
                if line.startswith(output) and any(after.startswith("sf> ") for after in lines[index + 1:]):
                    return screen
            time.sleep(0.05)
        raise AssertionError(f"no prompt after {output!r}:\n{screen}")

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        if self.qmp is not None:
            self.stream.close()
            self.qmp.close()
        self.log.close()


class EmulatorTests(unittest.TestCase):
    def test_workbench_loading_and_persistence(self):
        with tempfile.TemporaryDirectory(prefix="workbench-", dir=ROOT / "tmp") as directory:
            work = Path(directory)
            image = bytearray((ROOT / "sectorforth.img").read_bytes())
            for lba, text in {
                32: ": from32 1234 ; next-source",
                33: ": from33 2345 ;",
                34: "35 sector-evaluate 41",
                35: ": nested 17 ; 1 2 +",
                36: "101", 37: "202", 38: "303",
                39: "39 sector-evaluate",
                40: "blk @ 3 load blk @", 41: "blk @",
            }.items():
                source = work / f"sector-{lba}.f"
                source.write_text(text)
                image[lba * 512:(lba + 1) * 512] = builder.source_sector(source)[0]
            path = work / "workbench.img"
            path.write_bytes(image)
            qemu = Qemu(work, path, readonly=False)
            try:
                qemu.wait_for("Booting from Floppy")
                time.sleep(0.5)
                qemu.type("boot\n")
                qemu.wait_for("sf> ", timeout=60)
                sequence = 9000

                def check(command, output=""):
                    nonlocal sequence
                    sequence += 1
                    qemu.type(f"{command} {sequence} .\n")
                    return qemu.prompt_after(f"{output}{sequence} ")

                check("2 3 + .", "5 ")
                check("0 0= . 1 0= . -1 0= . 32768 0= .", "-1 0 0 0 ")
                check("123 dup + . 1 2 over + + .", "246 4 ")
                check("disk-sectors . 328 block>sector .", "720 718 ")
                check("719 source-data read-sector . 720 source-data read-sector .", "0 -1 ")
                check("-32768 . 65535 u. space", "-32768 65535 ")
                check("32 sector-evaluate from32 from33 + .", "3579 ")
                check("1 1 6 chs>sector .", "32 ")
                qemu.type("1 1 6 load-chs\n")
                qemu.prompt_after("sf> 1 1 6 load-chs")
                check("from32 from33 + .", "3579 ")
                check("34 sector-evaluate + . nested .", "44 17 ")
                check("36 38 sector-thru + + .", "606 ")
                check("36 source-data read-sector . source-data 3 evaluate .", "0 101 ")
                check("36 source-data read-sector drop source-data source-data 1+ 3 move source-data 1+ 3 type space", "101 ")
                check(": compiled 12345 ; compiled .", "12345 ")
                print("\n  logical, sequential, nested and range evaluation passed", flush=True)
                check("1 blank-block")
                qemu.type("0 1 edit-line\n")
                qemu.wait_for("edit> ")
                qemu.type("123 456 + . 99\n")
                qemu.prompt_after("edit> 123 456 + . 99")
                check("save-buffers flush 1 load .", "579 99 ")
                self.assertEqual(path.read_bytes()[64 * 512:64 * 512 + 11], b"123 456 + .")
                # Listing must preserve the stack, rather than execute the
                # source and leave its trailing 99 on top of our sentinel.
                check("777 1 list .", "777 ")
                check("4 blank-block 40 source-data read-sector drop source-data 4 block 18 move update save-buffers")
                check("3 blank-block 41 source-data read-sector drop source-data 3 block 5 move update save-buffers")
                check("4 load + + .", "11 ")
                check("3 4 thru + + + .", "14 ")
                check("328 blank-block save-buffers flush 328 load")
                print("  editing, buffered saves and nested block loading passed", flush=True)
                # Depth overflow must abort instead of overwriting reserved RAM.
                qemu.type("39 sector-evaluate\n")
                qemu.wait_for("!!", timeout=20)
                qemu.type("workbench\n")
                time.sleep(0.2)
                check("eval-depth @ .", "1 ")  # the command itself is evaluated
                check("1 load .", "579 99 ")
            except BaseException:
                print("\nWorkbench screen at failure:\n" + qemu.screen())
                print(qemu.monitor("info registers"))
                raise
            finally:
                qemu.close()
            # A new machine must read the saved source from disk, not RAM cache.
            qemu = Qemu(work, path)
            try:
                qemu.wait_for("Booting from Floppy")
                time.sleep(0.5)
                qemu.type("boot\n")
                qemu.wait_for("sf> ", timeout=60)
                qemu.type("1 load . 9876 .\n")
                qemu.prompt_after("579 99 9876 ")
                # BIOS write protection returns an error and restores BOOT code.
                qemu.type("64 source-data write-sector 0= . 9877 .\n")
                qemu.prompt_after("0 9877 ")
                qemu.type("1 load . 9878 .\n")
                qemu.prompt_after("579 99 9878 ")
                print("  reboot persistence and write-protection checks passed", flush=True)
            finally:
                qemu.close()

    def test_boot_and_addressed_source_loading(self):
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="qemu-", dir=ROOT / "tmp") as directory:
            work = Path(directory)
            empty = work / "empty.f"
            empty.write_text("")
            sources = [ROOT / "bootstrap.f"] + [empty] * 35
            # Each marker is defined by interpreted source, then invoked from
            # the keyboard. Test both heads, another cylinder, and source chaining.
            for index, name, number, tail in (
                (2, "third", 1, ""),
                (3, "fourth", 4, "0 0 5 load"),
                (4, "fifth", 5, ""),
                (9, "otherhead", 2, ""),
                (18, "othercylinder", 3, ""),
            ):
                path = work / f"{name}.f"
                path.write_text(f": {name} 4 2* 2* 2* 2* {number} + emit ; {tail}")
                sources[index - 1] = path
            image, _ = builder.build_image(ROOT / "sectorforth.bin", sources)
            image_path = work / "test.img"
            image_path.write_bytes(image)
            qemu = Qemu(work, image_path)
            try:
                qemu.wait_for("Booting from Floppy")
                time.sleep(0.5)
                # Ignored Backspace must neither erase 'o' nor enter the TIB.
                qemu.type("bo\bot\n")
                time.sleep(0.2)
                for command, marker in (
                    ("0 0 3 load\nthird\n", "third A"),
                    ("0 1 1 load\notherhead\n", "otherhead B"),
                    ("1 0 1 load\nothercylinder\n", "othercylinder C"),
                    ("0 0 4 load\nfourth fifth\n", "fourth fifth DE"),
                ):
                    qemu.type(command)
                    screen = qemu.wait_for(marker)
                    self.assertNotIn("!!", screen)
                # Successful LOAD restores BOOT to CHS 0/0/2. Lose the input
                # tail on purpose: 'missing' must never be interpreted.
                qemu.type("boot missing\n")
                time.sleep(0.2)
                qemu.type("0 0 3 load\nthird third\n")
                screen = qemu.wait_for("third third AA")
                self.assertNotIn("!!", screen)
                # BIOS failure must restore BOOT's fixed address as well as
                # reset the interpreter, even after patching the disk operands.
                qemu.type("0 2 0 load\n")  # invalid head and sector
                before = qemu.wait_for("!!")
                qemu.type("boot\n")
                time.sleep(0.2)
                self.assertEqual(qemu.screen().count("!!"), before.count("!!"))
                qemu.type("0 0 3 load\nthird third third\n")
                qemu.wait_for("third third third AAA")
            except BaseException:
                print("\nQEMU screen at failure:\n" + qemu.screen())
                raise
            finally:
                qemu.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
