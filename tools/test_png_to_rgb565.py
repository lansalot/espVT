import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from png_to_rgb565 import read_png


def chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", zlib.crc32(kind + payload))
    )


def png(width: int, height: int, rows: bytes, color_type: int = 2) -> bytes:
    header = struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0)
    compressed = zlib.compress(rows)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", compressed[:2])
        + chunk(b"IDAT", compressed[2:])
        + chunk(b"IEND", b"")
    )


class ReadPngTests(unittest.TestCase):
    def read(self, data: bytes):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.png"
            path.write_bytes(data)
            return read_png(path)

    def test_all_row_filters_and_split_idat(self):
        rows = bytes([
            0, 10, 20, 30, 40, 50, 60,
            1, 10, 20, 30, 30, 30, 30,
            2, 0, 0, 0, 0, 0, 0,
            3, 5, 10, 15, 15, 15, 15,
            4, 0, 0, 0, 0, 0, 0,
        ])
        width, height, pixels = self.read(png(2, 5, rows))
        self.assertEqual((width, height), (2, 5))
        self.assertEqual(pixels, [(10, 20, 30), (40, 50, 60)] * 5)

    def test_rejects_unsupported_color_type(self):
        with self.assertRaisesRegex(ValueError, "8-bit RGB"):
            self.read(png(1, 1, b"\x00\x01\x02\x03\xff", color_type=6))

    def test_rejects_corrupt_chunk(self):
        data = bytearray(png(1, 1, b"\x00\x01\x02\x03"))
        data[29] ^= 1
        with self.assertRaisesRegex(ValueError, "checksum"):
            self.read(data)

    def test_rejects_truncated_pixels(self):
        with self.assertRaisesRegex(ValueError, "pixel data length"):
            self.read(png(1, 1, b"\x00\x01\x02"))


if __name__ == "__main__":
    unittest.main()
