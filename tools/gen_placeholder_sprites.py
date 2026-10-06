#!/usr/bin/env python3
"""Generates placeholder pixel-art sprites for the MVP.

No third-party dependencies: PNGs are written with zlib + struct.
Real art replaces these files 1:1 (same paths, same frame layout),
so gameplay code and data files do not change.

Usage: python3 tools/gen_placeholder_sprites.py
"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "game" / "assets"

Color = tuple[int, int, int, int]
T: Color = (0, 0, 0, 0)


def hex_color(value: str) -> Color:
    value = value.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), 255)


class Canvas:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.px: list[list[Color]] = [[T] * width for _ in range(height)]

    def set(self, x: int, y: int, c: Color) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.px[y][x] = c

    def rect(self, x: int, y: int, w: int, h: int, c: Color) -> None:
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.set(xx, yy, c)

    def circle(self, cx: float, cy: float, r: float, c: Color) -> None:
        for yy in range(self.height):
            for xx in range(self.width):
                if (xx + 0.5 - cx) ** 2 + (yy + 0.5 - cy) ** 2 <= r * r:
                    self.set(xx, yy, c)

    def ring(self, cx: float, cy: float, r: float, thickness: float, c: Color) -> None:
        for yy in range(self.height):
            for xx in range(self.width):
                d = ((xx + 0.5 - cx) ** 2 + (yy + 0.5 - cy) ** 2) ** 0.5
                if r - thickness <= d <= r:
                    self.set(xx, yy, c)

    def outline(self, c: Color) -> None:
        """Adds a 1px outline around non-transparent pixels."""
        src = [row[:] for row in self.px]
        for y in range(self.height):
            for x in range(self.width):
                if src[y][x][3] != 0:
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.width and 0 <= ny < self.height and src[ny][nx][3] != 0 and src[ny][nx] != c:
                        self.px[y][x] = c
                        break

    def blit(self, other: "Canvas", ox: int, oy: int) -> None:
        for y in range(other.height):
            for x in range(other.width):
                if other.px[y][x][3] != 0:
                    self.set(ox + x, oy + y, other.px[y][x])


def save_png(canvas: Canvas, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = b"".join(b"\x00" + b"".join(bytes(p) for p in row) for row in canvas.px)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", canvas.width, canvas.height, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


def sheet(frames: list[Canvas]) -> Canvas:
    """Packs frames horizontally (Sprite2D.hframes = len(frames))."""
    w, h = frames[0].width, frames[0].height
    out = Canvas(w * len(frames), h)
    for i, f in enumerate(frames):
        out.blit(f, i * w, 0)
    return out


OUTLINE = hex_color("1a1423")


def humanoid(body: str, skin: str, accent: str, frame: int, weapon: str | None = None) -> Canvas:
    c = Canvas(16, 16)
    bob = frame  # 1px bob on second frame
    # legs
    leg = hex_color("3b2d3f")
    if frame == 0:
        c.rect(5, 12, 2, 3, leg)
        c.rect(9, 12, 2, 3, leg)
    else:
        c.rect(4, 12, 2, 3, leg)
        c.rect(10, 12, 2, 2, leg)
    # torso
    c.rect(4, 7 + bob, 8, 5, hex_color(body))
    c.rect(4, 10 + bob, 8, 1, hex_color(accent))
    # head
    c.rect(5, 2 + bob, 6, 5, hex_color(skin))
    c.set(6, 4 + bob, OUTLINE)
    c.set(9, 4 + bob, OUTLINE)
    if weapon:
        c.rect(13, 3 + bob, 1, 8, hex_color(weapon))
        c.rect(12, 9 + bob, 3, 1, hex_color("6b4f3a"))
    c.outline(OUTLINE)
    return c


def wolf(frame: int) -> Canvas:
    c = Canvas(16, 16)
    fur = hex_color("7a7a8c")
    c.rect(3, 7, 9, 4, fur)
    c.rect(11, 5, 4, 4, fur)
    c.set(13, 6, hex_color("f2d14b"))
    c.rect(1, 6, 2, 2, fur)
    leg = hex_color("4d4d5c")
    if frame == 0:
        for x in (3, 5, 9, 11):
            c.rect(x, 11, 1, 3, leg)
    else:
        for x in (2, 6, 8, 12):
            c.rect(x, 11, 1, 3, leg)
    c.outline(OUTLINE)
    return c


def slime(frame: int) -> Canvas:
    c = Canvas(16, 16)
    green = hex_color("5fcf6a")
    if frame == 0:
        c.circle(8, 10, 5.5, green)
        c.rect(2, 10, 12, 4, green)
    else:
        c.circle(8, 11, 5, green)
        c.rect(1, 11, 14, 3, green)
    c.rect(5, 9, 2, 2, hex_color("ffffff"))
    c.rect(9, 9, 2, 2, hex_color("ffffff"))
    c.set(6, 10, OUTLINE)
    c.set(10, 10, OUTLINE)
    c.outline(OUTLINE)
    return c


def guardian(frame: int) -> Canvas:
    c = Canvas(32, 32)
    bark = hex_color("6b4f3a")
    leaf = hex_color("3f8f4a")
    bob = frame
    c.circle(16, 9 + bob, 9, leaf)
    c.rect(10, 14 + bob, 12, 12, bark)
    c.rect(6, 16 + bob, 4, 8, bark)
    c.rect(22, 16 + bob, 4, 8, bark)
    if frame == 0:
        c.rect(11, 26, 4, 5, bark)
        c.rect(17, 26, 4, 5, bark)
    else:
        c.rect(10, 26, 4, 4, bark)
        c.rect(18, 26, 4, 5, bark)
    c.rect(13, 17 + bob, 2, 2, hex_color("ffcf4d"))
    c.rect(18, 17 + bob, 2, 2, hex_color("ffcf4d"))
    c.outline(OUTLINE)
    return c


def potion() -> Canvas:
    c = Canvas(16, 16)
    c.rect(7, 2, 2, 3, hex_color("c9c9d6"))
    c.circle(8, 10, 4.5, hex_color("d94b5a"))
    c.set(6, 8, hex_color("ffffff"))
    c.outline(OUTLINE)
    return c


def sword() -> Canvas:
    c = Canvas(16, 16)
    blade = hex_color("d6d6e6")
    for i in range(9):
        c.set(4 + i, 11 - i, blade)
        c.set(5 + i, 11 - i, blade)
    c.rect(2, 11, 5, 1, hex_color("8a6a3a"))
    c.rect(3, 12, 2, 2, hex_color("6b4f3a"))
    c.outline(OUTLINE)
    return c


def coin() -> Canvas:
    c = Canvas(8, 8)
    c.circle(4, 4, 3.5, hex_color("f2c14e"))
    c.rect(3, 2, 1, 4, hex_color("fff0a8"))
    c.outline(OUTLINE)
    return c


def arrow() -> Canvas:
    c = Canvas(8, 8)
    c.rect(0, 3, 6, 1, hex_color("c9a46b"))
    c.rect(6, 2, 1, 3, hex_color("e6e6f0"))
    c.set(7, 3, hex_color("e6e6f0"))
    return c


def bolt() -> Canvas:
    c = Canvas(8, 8)
    c.circle(4, 4, 3, hex_color("9be15d"))
    c.circle(4, 4, 1.5, hex_color("e8ffd0"))
    return c


def slash() -> Canvas:
    c = Canvas(32, 32)
    c.ring(16, 16, 15, 3, hex_color("ffffff"))
    # keep only the right half: the node is rotated toward the target
    for y in range(32):
        for x in range(16):
            c.set(x, y, T)
    return c


def nova() -> Canvas:
    c = Canvas(64, 64)
    c.ring(32, 32, 31, 3, hex_color("ffd36b"))
    c.ring(32, 32, 26, 1, hex_color("fff3c4"))
    return c


def tile(base: str, dots: list[tuple[int, int, str]]) -> Canvas:
    c = Canvas(16, 16)
    c.rect(0, 0, 16, 16, hex_color(base))
    for x, y, col in dots:
        c.set(x, y, hex_color(col))
    return c


def main() -> None:
    save_png(sheet([humanoid("4a6fa5", "f2c9a0", "c9a227", f, "d6d6e6") for f in (0, 1)]),
             ROOT / "sprites/characters/warrior.png")
    save_png(sheet([humanoid("7b4fa5", "f2c9a0", "e0e0ff", f, "8a6a3a") for f in (0, 1)]),
             ROOT / "sprites/characters/mage.png")
    save_png(sheet([humanoid("5a8f3a", "8fbf5a", "3b2d3f", f, "8a8a99") for f in (0, 1)]),
             ROOT / "sprites/enemies/goblin.png")
    save_png(sheet([humanoid("d8d8cc", "eeeedd", "6b6b5c", f, "8a6a3a") for f in (0, 1)]),
             ROOT / "sprites/enemies/skeleton.png")
    save_png(sheet([wolf(f) for f in (0, 1)]), ROOT / "sprites/enemies/wolf.png")
    save_png(sheet([slime(f) for f in (0, 1)]), ROOT / "sprites/enemies/slime.png")
    save_png(sheet([guardian(f) for f in (0, 1)]), ROOT / "sprites/enemies/forest_guardian.png")
    save_png(potion(), ROOT / "sprites/items/health_potion.png")
    save_png(sword(), ROOT / "sprites/items/iron_sword.png")
    save_png(coin(), ROOT / "sprites/items/gold_coin.png")
    save_png(arrow(), ROOT / "sprites/projectiles/arrow.png")
    save_png(bolt(), ROOT / "sprites/projectiles/bolt.png")
    save_png(slash(), ROOT / "sprites/vfx/slash.png")
    save_png(nova(), ROOT / "sprites/vfx/nova.png")
    save_png(tile("3d6b3f", [(3, 4, "4f8a4f"), (11, 9, "4f8a4f"), (7, 13, "335a35"), (13, 2, "335a35")]),
             ROOT / "tilesets/grass.png")
    save_png(tile("3a3340", [(2, 5, "4a4252"), (10, 11, "4a4252"), (6, 1, "2c2632"), (14, 14, "2c2632")]),
             ROOT / "tilesets/cave.png")
    print(f"Sprites written to {ROOT}")


if __name__ == "__main__":
    main()
