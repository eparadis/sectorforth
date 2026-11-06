#!/usr/bin/env python3
"""Image-format checks and a real BIOS/keyboard/Forth integration test in QEMU."""

import importlib.util
import json
from pathlib import Path
import socket
import subprocess
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
        self.assertEqual(len(image), 1474560)
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


class Qemu:
    def __init__(self, work, image):
        self.work = work
        self.sequence = 0
        self.qmp = None
        self.log = (work / "qemu.log").open("w+")
        self.process = subprocess.Popen([
            "qemu-system-i386", "-machine", "pc", "-m", "16",
            "-drive", f"file={image},format=raw,if=floppy,readonly=on",
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
        names = {" ": "spc", "\n": "ret", "\b": "backspace"}
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
        return "\n".join(chars[i:i + 80].decode("cp437") for i in range(0, 2000, 80))

    def wait_for(self, text):
        deadline = time.monotonic() + 10
        screen = ""
        while time.monotonic() < deadline:
            screen = self.screen()
            if text in screen:
                return screen
            time.sleep(0.05)
        raise AssertionError(f"screen never contained {text!r}:\n{screen}")

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
                (18, "otherhead", 2, ""),
                (36, "othercylinder", 3, ""),
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
