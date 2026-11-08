"""Generate a standalone 512px PNG avatar using only the Python standard library."""

from pathlib import Path
import struct
import zlib


def generate():
    size = 512
    pixels = bytearray(bytes((6, 126, 117)) * size * size)

    def capsule(x, y, width, height, color):
        radius = min(width, height) / 2
        for py in range(y, y + height):
            for px in range(x, x + width):
                cx = min(max(px + 0.5, x + radius), x + width - radius)
                cy = min(max(py + 0.5, y + radius), y + height - radius)
                if (px + 0.5 - cx) ** 2 + (py + 0.5 - cy) ** 2 <= radius ** 2:
                    index = (py * size + px) * 3
                    pixels[index:index + 3] = bytes(color)

    white = (255, 255, 255)
    for x, height in ((96, 74), (138, 136), (180, 202), (222, 114)):
        capsule(x, 256 - height // 2, 24, height, white)
    for y, width in ((196, 124), (244, 100), (292, 124)):
        capsule(292, y, width, 20, white)

    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))

    rows = b''.join(b'\x00' + pixels[y * size * 3:(y + 1) * size * 3] for y in range(size))
    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b'')
    target = Path(__file__).resolve().parents[1] / 'docs/miniprogram/assets/avatar.png'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(png)
    print(target)


if __name__ == '__main__':
    generate()
