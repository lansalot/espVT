#!/usr/bin/env python3
"""Convert a non-interlaced 8-bit RGB PNG logo to a cropped RGB565 header."""

import argparse
import struct
import zlib
from pathlib import Path

from bmp_to_rgb565 import crop_to_content, resize, write_header


def read_png(path: Path) -> tuple[int, int, list[tuple[int, int, int]]]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Expected a PNG file")

    position = 8
    header = None
    image_data = bytearray()
    finished = False
    while position + 12 <= len(data):
        length = struct.unpack_from(">I", data, position)[0]
        end = position + 12 + length
        if end > len(data):
            raise ValueError("Truncated PNG chunk")
        kind = data[position + 4 : position + 8]
        payload = data[position + 8 : position + 8 + length]
        checksum = struct.unpack_from(">I", data, position + 8 + length)[0]
        if zlib.crc32(kind + payload) != checksum:
            raise ValueError("Invalid PNG chunk checksum")
        if kind == b"IHDR":
            if header is not None or length != 13:
                raise ValueError("Invalid PNG header")
            header = struct.unpack(">IIBBBBB", payload)
        elif kind == b"IDAT":
            image_data.extend(payload)
        elif kind == b"IEND":
            finished = True
            break
        position = end

    if header is None or not image_data or not finished:
        raise ValueError("Incomplete PNG file")
    width, height, depth, color_type, compression, filtering, interlace = header
    if not width or not height:
        raise ValueError("Invalid PNG dimensions")
    if (depth, color_type, compression, filtering, interlace) != (8, 2, 0, 0, 0):
        raise ValueError("Only non-interlaced 8-bit RGB PNG input is supported")

    raw = zlib.decompress(image_data)
    stride = width * 3
    if len(raw) != (stride + 1) * height:
        raise ValueError("Invalid PNG pixel data length")

    pixels = []
    previous = bytearray(stride)
    for y in range(height):
        start = y * (stride + 1)
        filter_type = raw[start]
        row = bytearray(raw[start + 1 : start + 1 + stride])
        if filter_type > 4:
            raise ValueError("Unsupported PNG filter")
        for i in range(stride):
            left = row[i - 3] if i >= 3 else 0
            above = previous[i]
            upper_left = previous[i - 3] if i >= 3 else 0
            if filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = above
            elif filter_type == 3:
                predictor = (left + above) // 2
            elif filter_type == 4:
                estimate = left + above - upper_left
                distances = (abs(estimate - left), abs(estimate - above), abs(estimate - upper_left))
                predictor = (left, above, upper_left)[distances.index(min(distances))]
            else:
                predictor = 0
            row[i] = (row[i] + predictor) & 0xFF
        pixels.extend((row[i], row[i + 1], row[i + 2]) for i in range(0, stride, 3))
        previous = row
    return width, height, pixels


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--max-width", type=int, required=True)
    parser.add_argument("--max-height", type=int, required=True)
    parser.add_argument("--padding", type=int, default=12)
    args = parser.parse_args()

    width, height, pixels = read_png(args.input)
    width, height, pixels = crop_to_content(width, height, pixels, args.padding)
    width, height, pixels = resize(width, height, pixels, args.max_width, args.max_height)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_header(args.output, width, height, pixels)
    print(f"Generated {args.output.name}: {width}x{height} RGB565")


if __name__ == "__main__":
    main()
