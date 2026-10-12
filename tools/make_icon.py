"""Draw the Petrolmate integration icon (pure stdlib — no PIL needed).

White fuel pump with an amber price screen on a teal rounded square.
Writes brand/icon.png (256), brand/icon@2x.png (512) and dark_ variants (same art; it reads on both).
Run: python3 tools/make_icon.py
"""

import math
import struct
import zlib
from pathlib import Path

TEAL = (15, 118, 110)
WHITE = (255, 255, 255)
AMBER = (251, 191, 36)


def rrect(x, y, x0, y0, x1, y1, r):
    """Signed distance to a rounded rectangle (negative inside)."""
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hx, hy = (x1 - x0) / 2 - r, (y1 - y0) / 2 - r
    dx, dy = abs(x - cx) - hx, abs(y - cy) - hy
    return math.hypot(max(dx, 0), max(dy, 0)) + min(max(dx, dy), 0) - r


def capsule(x, y, ax, ay, bx, by, r):
    """Signed distance to a thick line segment with round ends."""
    px, py, vx, vy = x - ax, y - ay, bx - ax, by - ay
    t = max(0, min(1, (px * vx + py * vy) / (vx * vx + vy * vy)))
    return math.hypot(px - vx * t, py - vy * t) - r


def colour_at(x, y):
    """Colour (or None = transparent) at a point on a 512 canvas."""
    if rrect(x, y, 16, 16, 496, 496, 110) > 0:
        return None
    # price screen sits on top of the pump body
    if rrect(x, y, 182, 158, 290, 236, 12) <= 0:
        return AMBER
    pump = min(
        rrect(x, y, 152, 118, 320, 398, 26),          # body
        rrect(x, y, 122, 384, 350, 424, 12),          # base
        rrect(x, y, 350, 132, 402, 206, 14),          # nozzle
        capsule(x, y, 376, 200, 376, 318, 13),        # hose down
        capsule(x, y, 376, 318, 350, 346, 13),        # hose bend
        capsule(x, y, 350, 346, 318, 346, 13),        # hose back into the body
    )
    return WHITE if pump <= 0 else TEAL


def render(size, ss=4):
    scale = 512 / size
    rows = []
    for j in range(size):
        row = bytearray([0])  # PNG filter: none
        for i in range(size):
            acc = [0, 0, 0, 0]
            for sj in range(ss):
                for si in range(ss):
                    c = colour_at((i + (si + .5) / ss) * scale, (j + (sj + .5) / ss) * scale)
                    if c:
                        acc[0] += c[0]; acc[1] += c[1]; acc[2] += c[2]; acc[3] += 255
            n = ss * ss
            a = acc[3] / n
            if a:
                k = 255 / acc[3]
                row += bytes([round(acc[0] * k), round(acc[1] * k), round(acc[2] * k), round(a)])
            else:
                row += b"\0\0\0\0"
        rows.append(bytes(row))
    raw = b"".join(rows)

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "custom_components" / "petrolmate" / "brand"
    out.mkdir(parents=True, exist_ok=True)
    for name, size in (("icon.png", 256), ("icon@2x.png", 512)):
        png = render(size)
        (out / name).write_bytes(png)
        (out / f"dark_{name}").write_bytes(png)
        print(out / name, len(png))
