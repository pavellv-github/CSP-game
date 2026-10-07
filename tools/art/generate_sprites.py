#!/usr/bin/env python3
"""Pixel Fantasy Survival - procedural pixel-art generator (style v2).

Everything is drawn pixel by pixel at native resolution from one master
palette v2 (40 colours, warm daylight, outline #2a1d16, flat 2-3 tone ramps,
no baked shadows) and written as PNG with zlib + struct (stdlib only).
Style: docs/art/ART_BRIEF.md section 1a, target docs/art/reference/style_target_base.png.

    python3 tools/art/generate_sprites.py              # regenerate all game assets
    python3 tools/art/generate_sprites.py --preview DIR  # also write upscaled previews

Sprite sheet contract (docs/art/GENERATED_ART.md):
    one PNG per character, row = animation, column = frame, no padding.
    rows: 0 idle(4) 1 walk(6) 2 attack(5, hit 2) 3 hurt(2) 4 death(6) [5 cast(4), hero only]
    feet (pivot) on the same line in every frame, 1 px margin below.
    Everything faces RIGHT; the game mirrors for left.
"""
from __future__ import annotations

import math
import random
import struct
import sys
import zlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ASSETS = REPO / "game" / "assets"

# --------------------------------------------------------------------------------------
# Master palette v2 (style v2, docs/art/ART_BRIEF.md section 1a): warm sunny daylight,
# dark-brown outline #2a1d16, flat 2-3 tone ramps per material. 40 unique colours.
# One character per colour so parts can be drawn as ASCII pixel maps; a few keys are
# aliases of the same colour (e == R, D == k) so older drawings keep working.
# --------------------------------------------------------------------------------------
PALETTE: dict[str, str] = {
    "o": "2a1d16",  # outline (the only outline colour)
    "k": "4a3226",  # deep warm brown (darkest inner tone, dark wood)
    "a": "6e4529",  # leather 1 (shadow)
    "b": "9a6236",  # leather 2 (base)
    "c": "c4884a",  # leather 3 (light)
    "d": "e6b874",  # leather 4 / straw highlight
    "e": "963a22",  # rust fur 1 / blood red (shared)
    "f": "d0682e",  # rust fur 2
    "g": "f4a04e",  # rust fur 3
    "h": "b8704a",  # skin 1 (shadow)
    "i": "e6a676",  # skin 2
    "j": "fcd4a2",  # skin 3 (light)
    "m": "5e5758",  # steel / stone 1 (warm grey shadow)
    "n": "908a86",  # steel / stone 2
    "p": "cdc8bc",  # steel / stone 3 (light)
    "q": "a46c28",  # bronze
    "r": "e8b040",  # gold
    "s": "fde890",  # pale gold / light
    "t": "2f4d2c",  # foliage 1 (darkest green)
    "u": "4b7034",  # foliage 2
    "v": "76983c",  # foliage 3
    "w": "a8c04e",  # foliage 4 (lit leaves)
    "x": "dae47c",  # foliage 5 / spore glow
    "y": "a89a7e",  # bone 1 (shadow)
    "z": "e6dab4",  # bone 2
    "W": "fff8e4",  # parchment white (highlights, VFX)
    "R": "963a22",  # red 1 (alias of e)
    "S": "d85440",  # red 2
    "A": "2c5e98",  # blue 1
    "B": "4e98d4",  # blue 2
    "C": "a6e0f4",  # blue 3 (ice / glow)
    "D": "4a3226",  # alias of k (old "cave dark" key)
    "K": "3c2854",  # purple 1
    "L": "5f3e86",  # purple 2
    "M": "8e66b8",  # purple 3
    "N": "cca6ec",  # violet glow
    # ground-only tones: deliberately close to each other so floors stay calm
    "G": "b2a462",  # meadow base (sun-dried olive-ochre)
    "H": "a69959",  # meadow shade
    "E": "9a7c58",  # trampled earth (dirt patch centre)
    "F": "a88f62",  # trampled earth edge (between earth and meadow)
    "P": "857461",  # cave floor base (warm brown-grey)
    "Q": "786855",  # cave floor shade
}
UNIQUE_COLOURS = sorted(set(PALETTE.values()), key=list(PALETTE.values()).index)
assert len(UNIQUE_COLOURS) <= 40, len(UNIQUE_COLOURS)
RGBA = {k: (int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16), 255) for k, v in PALETTE.items()}

# Ramps: one step darker / lighter inside the same material (never jumps to the outline
# colour except from the darkest tone, so inner lines stay "a tone darker than the fill").
DARKER = {"d": "c", "c": "b", "b": "a", "a": "k", "k": "o", "g": "f", "f": "e", "e": "k",
          "j": "i", "i": "h", "h": "e", "p": "n", "n": "m", "m": "k", "D": "o", "s": "r", "r": "q",
          "q": "a", "x": "w", "w": "v", "v": "u", "u": "t", "t": "o", "z": "y", "y": "m", "W": "z",
          "S": "R", "R": "k", "C": "B", "B": "A", "A": "K", "o": "o",
          "N": "M", "M": "L", "L": "K", "K": "o", "G": "H", "H": "E", "E": "a", "F": "E", "P": "Q", "Q": "m"}
LIGHTER = {"o": "k", "k": "a", "a": "b", "b": "c", "c": "d", "d": "j", "e": "f", "f": "g", "g": "s",
           "h": "i", "i": "j", "j": "W", "D": "a", "m": "n", "n": "p", "p": "W", "q": "r", "r": "s",
           "s": "W", "t": "u", "u": "v", "v": "w", "w": "x", "x": "s", "y": "z", "z": "W", "W": "W",
           "R": "S", "S": "g", "A": "B", "B": "C", "C": "W",
           "K": "L", "L": "M", "M": "N", "N": "W", "G": "w", "H": "G", "E": "F", "F": "G", "P": "n", "Q": "P"}

LIGHT = (-0.6, -0.8)  # light from top-left


# --------------------------------------------------------------------------------------
# Canvas
# --------------------------------------------------------------------------------------
class Canvas:
    def __init__(self, w: int, h: int) -> None:
        self.w, self.h = w, h
        self.px: list[list[str | None]] = [[None] * w for _ in range(h)]

    def copy(self) -> "Canvas":
        c = Canvas(self.w, self.h)
        c.px = [row[:] for row in self.px]
        return c

    def get(self, x: int, y: int) -> str | None:
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.px[y][x]
        return None

    def set(self, x: float, y: float, c: str | None) -> None:
        x, y = int(math.floor(x)), int(math.floor(y))
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y][x] = c

    def rect(self, x: int, y: int, w: int, h: int, c: str) -> None:
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.set(xx, yy, c)

    def line(self, x0: float, y0: float, x1: float, y1: float, c: str) -> None:
        x0, y0, x1, y1 = round(x0), round(y0), round(x1), round(y1)
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            self.set(x0, y0, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def ellipse(self, cx: float, cy: float, rx: float, ry: float, c: str) -> None:
        for yy in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for xx in range(int(cx - rx) - 1, int(cx + rx) + 2):
                if ((xx + 0.5 - cx) / rx) ** 2 + ((yy + 0.5 - cy) / ry) ** 2 <= 1.0:
                    self.set(xx, yy, c)

    def shaded_ellipse(self, cx: float, cy: float, rx: float, ry: float, ramp: str,
                       bias: float = 0.0, rim: bool = False) -> None:
        """Ellipse lit from top-left. ramp = dark..light colour keys."""
        n = len(ramp)
        for yy in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for xx in range(int(cx - rx) - 1, int(cx + rx) + 2):
                nx, ny = (xx + 0.5 - cx) / rx, (yy + 0.5 - cy) / ry
                d = nx * nx + ny * ny
                if d > 1.0:
                    continue
                nz = math.sqrt(max(0.0, 1.0 - d))
                lum = -(nx * LIGHT[0] + ny * LIGHT[1]) * 0.75 + nz * 0.55 + bias
                idx = int((lum + 0.35) / 1.25 * n)
                if rim and d > 0.72 and nx > 0.1:
                    idx -= 1
                self.set(xx, yy, ramp[max(0, min(n - 1, idx))])

    def stamp(self, art: list[str] | tuple[str, ...], x: int, y: int, flip: bool = False,
              remap: dict[str, str] | None = None) -> None:
        for j, row in enumerate(art):
            if flip:
                row = row[::-1]
            for i, ch in enumerate(row):
                if ch in (".", " "):
                    continue
                if remap:
                    ch = remap.get(ch, ch)
                self.set(x + i, y + j, ch)

    def blit(self, other: "Canvas", ox: int, oy: int) -> None:
        for y in range(other.h):
            for x in range(other.w):
                if other.px[y][x] is not None:
                    self.set(ox + x, oy + y, other.px[y][x])

    def recolor(self, mapping: dict[str, str], keep: str = "o") -> None:
        for row in self.px:
            for i, c in enumerate(row):
                if c is not None and c not in keep:
                    row[i] = mapping.get(c, c)

    def outline(self, c: str = "o", diagonal: bool = False) -> None:
        src = [row[:] for row in self.px]
        nb = ((1, 0), (-1, 0), (0, 1), (0, -1))
        if diagonal:
            nb += ((1, 1), (-1, -1), (1, -1), (-1, 1))
        for y in range(self.h):
            for x in range(self.w):
                if src[y][x] is not None:
                    continue
                for dx, dy in nb:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.w and 0 <= ny < self.h and src[ny][nx] not in (None, c):
                        self.px[y][x] = c
                        break

    def bbox(self) -> tuple[int, int, int, int] | None:
        xs, ys = [], []
        for y in range(self.h):
            for x in range(self.w):
                if self.px[y][x] is not None:
                    xs.append(x)
                    ys.append(y)
        if not xs:
            return None
        return min(xs), min(ys), max(xs), max(ys)

    def shifted(self, dx: int, dy: int) -> "Canvas":
        c = Canvas(self.w, self.h)
        c.blit(self, dx, dy)
        return c

    def rotated(self, deg: float, px: float, py: float) -> "Canvas":
        """Nearest-neighbour rotation about (px, py); negative deg = counter-clockwise."""
        out = Canvas(self.w, self.h)
        t = math.radians(deg)
        ct, st = math.cos(t), math.sin(t)
        for y in range(self.h):
            for x in range(self.w):
                dx, dy = x + 0.5 - px, y + 0.5 - py
                sx = dx * ct + dy * st + px
                sy = -dx * st + dy * ct + py
                out.px[y][x] = self.get(int(math.floor(sx)), int(math.floor(sy)))
        return out

    def mirrored(self) -> "Canvas":
        c = Canvas(self.w, self.h)
        c.px = [row[::-1] for row in self.px]
        return c

    def keep(self, pred) -> None:
        for y in range(self.h):
            for x in range(self.w):
                if not pred(x, y):
                    self.px[y][x] = None


def clump(c: Canvas, cx: float, cy: float, rx: float, ry: float, lit: str, mid: str, dark: str,
          rim: float = 1.6) -> None:
    """Flat 3-tone blob (style v2): mid fill, lit crescent top-left, dark crescent bottom-right."""
    def inside(x: float, y: float) -> bool:
        return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0
    for yy in range(int(cy - ry) - 1, int(cy + ry) + 2):
        for xx in range(int(cx - rx) - 1, int(cx + rx) + 2):
            x, y = xx + 0.5, yy + 0.5
            if not inside(x, y):
                continue
            if not inside(x - rim * 0.7, y - rim):
                col = lit
            elif not inside(x + rim * 0.9, y + rim * 1.1):
                col = dark
            else:
                col = mid
            c.set(xx, yy, col)


def to_rgba(c: Canvas, bg: tuple[int, int, int, int] | None = None) -> list[list[tuple[int, int, int, int]]]:
    t = bg or (0, 0, 0, 0)
    return [[RGBA[p] if p is not None else t for p in row] for row in c.px]


def write_png(rows: list[list[tuple[int, int, int, int]]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    h, w = len(rows), len(rows[0])
    raw = b"".join(b"\x00" + bytes(v for p in row for v in p) for row in rows)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    path.write_bytes(png)


def save(c: Canvas, rel: str) -> None:
    write_png(to_rgba(c), ASSETS / rel)
    WRITTEN.append((rel, c.w, c.h))


WRITTEN: list[tuple[str, int, int]] = []


def finish(c: Canvas) -> Canvas:
    c.outline("o")
    return c


def flash(c: Canvas) -> Canvas:
    c = c.copy()
    c.recolor(LIGHTER)
    c.recolor(LIGHTER)
    return c


def build_sheet(rows: list[list[Canvas]], fw: int, fh: int) -> Canvas:
    cols = max(len(r) for r in rows)
    sheet = Canvas(fw * cols, fh * len(rows))
    for ri, frames in enumerate(rows):
        for ci, f in enumerate(frames):
            assert f.w == fw and f.h == fh
            # drawings put the feet on the 2nd-to-last row; lift by 1 so the outline
            # under the feet also keeps a 1 px transparent margin at the frame bottom
            sheet.blit(f.shifted(0, -1), ci * fw, ri * fh)
    return sheet


def fall_frames(make, base_pose: dict, foot_y: int, pivot_x: float, angles: list[float],
                w: int, h: int, pre: list[Canvas], last_remap: dict[str, str] | None = None) -> list[Canvas]:
    """Death: pre-made frames, then the un-outlined body rotated backwards about the feet.

    Rotation happens on a padded canvas so nothing is clipped; the result is then moved
    so it rests on the foot line and stays inside the frame."""
    frames = list(pre)
    pad = max(w, h)
    for ai, ang in enumerate(angles):
        body = make(**base_pose)
        big = Canvas(w + 2 * pad, h + 2 * pad)
        big.blit(body, pad, pad)
        rot = big.rotated(ang, pivot_x + pad, foot_y + 1 + pad)
        x0, y0, x1, y1 = rot.bbox()
        dx = 0
        if x0 - pad < 1:
            dx = 1 - (x0 - pad)
        if x1 - pad + dx > w - 2:
            dx = (w - 2) - (x1 - pad)
        dy = foot_y - (y1 - pad)
        out = Canvas(w, h)
        out.blit(rot, dx - pad, dy - pad)
        if last_remap and ai == len(angles) - 1:
            out.recolor(last_remap)
        frames.append(finish(out))
    return frames


# ======================================================================================
# Shared weapon: sword (heroes, sword icon)
# ======================================================================================
def draw_sword(c: Canvas, hx: float, hy: float, ang: float, length: int = 10) -> None:
    t = math.radians(ang)
    dx, dy = math.cos(t), math.sin(t)
    px_, py_ = -dy, dx  # perpendicular
    # grip + pommel behind the hand
    c.line(hx - dx * 2, hy - dy * 2, hx, hy, "b")
    c.set(round(hx - dx * 3), round(hy - dy * 3), "r")
    # guard
    gx, gy = hx + dx, hy + dy
    c.line(gx - px_ * 2, gy - py_ * 2, gx + px_ * 2, gy + py_ * 2, "q")
    c.set(round(gx - px_ * 2), round(gy - py_ * 2), "r")
    # blade: lit edge + shadow edge
    for i in range(2, length + 1):
        bx, by = hx + dx * i, hy + dy * i
        c.set(round(bx), round(by), "p" if i < length else "W")
        sx, sy = bx + px_, by + py_
        if c.get(round(sx), round(sy)) is None or i > 2:
            c.set(round(sx), round(sy), "n" if i < length - 1 else None)
    c.set(round(hx + dx * 4), round(hy + dy * 4), "W")


# ======================================================================================
# GOBLIN 24x24 (green, big ears, rag tunic, club)
# ======================================================================================
E_FOOT = 22

GOB_HEAD = [
    "x.....wwww..",
    "ww...wxxxww.",
    ".wwwwxxwwwwv",
    "..vwwxwwSoww",
    "...vvwwwwwwx",
    "....vvwwWvwv",
    ".....vvvvvv.",
]
GOB_BODY = [
    ".cddcc.",
    "bccdccb",
    "bcccccb",
    "aqrqqqa",
    "bcbbcbb",
    ".b.bb..",
]
GOB_LEG = ["wv", "wv", "vv", "vvw"]


def draw_club(c: Canvas, hx: float, hy: float, ang: float) -> None:
    t = math.radians(ang)
    dx, dy = math.cos(t), math.sin(t)
    c.line(hx - dx, hy - dy, hx + dx * 3, hy + dy * 3, "b")
    for i in range(3, 7):
        r = 1.4 if i > 3 else 1.0
        bx, by = hx + dx * i, hy + dy * i
        c.ellipse(bx + 0.5, by + 0.5, r, r, "c")
    c.set(round(hx + dx * 5 - dy), round(hy + dy * 5 + dx), "d")
    c.set(round(hx + dx * 6 + dy * 1.5), round(hy + dy * 6 - dx * 1.5), "n")
    c.set(round(hx + dx * 4 + dy * 1.5), round(hy + dy * 4 - dx * 1.5), "p")


def goblin(bob: int = 0, ldx: int = 0, rdx: int = 0, llift: int = 0, rlift: int = 0,
           hand: tuple[float, float] = (16, 15), club: float = 300, lean: int = 0, crouch: int = 0) -> Canvas:
    c = Canvas(24, 24)
    ub = bob + crouch
    c.stamp(GOB_LEG, 9 + ldx, 19 - llift, remap=DARKER)
    c.stamp(GOB_BODY, 8 + lean, 13 + ub)
    c.stamp(GOB_LEG, 12 + rdx, 19 - rlift)
    # back arm
    c.line(9 + lean, 15 + ub, 8 + lean, 17 + ub, "v")
    c.stamp(GOB_HEAD, 5 + lean, 6 + ub)
    hx, hy = hand[0] + lean, hand[1] + ub
    draw_club(c, hx, hy, club)
    c.line(13 + lean, 15 + ub, hx, hy, "w")
    c.set(hx, hy, "x")
    return c


def goblin_sheet() -> Canvas:
    F = finish
    idle = [F(goblin(bob=b, club=300 + b * 6)) for b in (0, 0, 1, 1)]
    walk = []
    for f in range(6):
        p = f / 6 * 2 * math.pi
        s = math.sin(p)
        d = round(1.6 * s)
        walk.append(F(goblin(bob=0 if abs(s) > 0.6 else 1, ldx=-d, rdx=d,
                             llift=1 if math.cos(p) < -0.5 else 0, rlift=1 if math.cos(p) > 0.5 else 0,
                             club=300 + d * 8)))
    attack = [
        F(goblin(hand=(12, 11), club=235, lean=-1)),
        F(goblin(hand=(13, 10), club=260, bob=-1, lean=-1)),
        F(goblin(hand=(17, 15), club=20, lean=1, crouch=1, ldx=-1, rdx=1)),
        F(goblin(hand=(17, 16), club=50, lean=1, crouch=1, ldx=-1, rdx=1)),
        F(goblin(hand=(15, 15), club=320)),
    ]
    hurt = [F(flash(goblin(lean=-1))), F(goblin(lean=-1))]
    death = fall_frames(goblin, dict(lean=-1, club=200, hand=(13, 16)), E_FOOT, 11, [-40, -75, -90, -90], 24, 24,
                        pre=[F(flash(goblin(lean=-1))), F(goblin(crouch=2, lean=-1))])
    return build_sheet([idle, walk, attack, hurt, death], 24, 24)


# ======================================================================================
# WOLF 24x24 (grey, quadruped, runs straight at the player)
# ======================================================================================
WOLF_HEAD = [
    ".n.n......",
    ".nnpn.....",
    "nnpppnn...",
    "nnpnnnpppp",
    "mnnnnppppk",
    ".mnnzzz...",
    "..mmz.....",
]
WOLF_HEAD_OPEN = [
    ".n.n......",
    ".nnpn.....",
    "nnpppnn...",
    "nnpnnnpppk",
    "mnnnnWW...",
    ".mnnz.....",
    "..mnzWzzz.",
]


def wolf(bob: int = 0, legs: tuple[int, int, int, int] = (0, 0, 0, 0), lifts=(0, 0, 0, 0), dx: int = 0,
         head_dy: int = 0, open_mouth: bool = False, drop: int = 0, leg_len: int = 7,
         tail: int = 0, eye_closed: bool = False) -> Canvas:
    c = Canvas(24, 24)
    by = 13 + bob + drop
    # far legs (darker)
    for i, (lx, base) in enumerate(((5, legs[1]), (13, legs[3]))):
        x = lx + base + dx
        ll = max(1, leg_len - lifts[[1, 3][i]])
        c.rect(x, by + 3, 2, ll - 1, "m")
        c.set(x + 1, by + 2 + ll, "m")
        c.set(x, by + 2 + ll, "D")
    # tail hangs down-back (wolf, not a curled dog tail)
    tx, ty = 4 + dx, by
    for k, (x, y) in enumerate(((0, 0), (-1, 1), (-2, 2), (-2, 3), (-3, 4))):
        yy = y - (tail * k) // 3
        c.ellipse(tx + x + 0.5, ty + yy + 0.5, 1.3, 1.3, "n" if k < 3 else "m")
    c.set(tx - 1, ty, "p")
    c.set(tx - 2, ty + 1, "p")
    # body
    c.shaded_ellipse(10.5 + dx, by + 2, 6.4, 3.6, "mnnp")
    for x in range(6, 15):
        c.set(x + dx, by - 1 + (1 if x in (6, 14) else 0), "m")
    for x in range(8, 13):
        c.set(x + dx, by + 4, "z" if x % 3 else "p")
    # near legs
    for i, (lx, base) in enumerate(((7, legs[0]), (15, legs[2]))):
        x = lx + base + dx
        ll = max(1, leg_len - lifts[[0, 2][i]])
        c.rect(x, by + 3, 2, ll - 1, "n")
        c.set(x, by + 3, "p")
        c.set(x, by + 2 + ll, "n")
        c.set(x + 1, by + 2 + ll, "n")
        c.set(x + 2, by + 2 + ll, "m")
    # neck ruff + head
    c.ellipse(15.5 + dx, by + 0.5, 2.4, 2.8, "n")
    c.set(14 + dx, by - 1, "p")
    art = WOLF_HEAD_OPEN if open_mouth else WOLF_HEAD
    hy = by - 5 + head_dy
    c.stamp(art, 13 + dx, hy)
    if eye_closed:
        c.set(17 + dx, hy + 3, "m")
        c.set(18 + dx, hy + 3, "o")
    else:
        c.set(18 + dx, hy + 3, "r")
        c.set(17 + dx, hy + 3, "o")
    return c


def wolf_sheet() -> Canvas:
    F = finish
    idle = [F(wolf(bob=b, tail=t)) for b, t in ((0, 0), (0, 1), (1, 1), (1, 0))]
    # gallop-ish trot: near/far pairs opposite
    pat = [(2, -1, -1, 2), (1, 0, 0, 1), (-1, 2, 2, -1), (-2, 1, 1, -2), (-1, 0, 0, -1), (1, -2, -2, 1)]
    lift = [(0, 1, 1, 0), (1, 0, 0, 1), (0, 1, 1, 0), (0, 0, 0, 0), (1, 0, 0, 1), (0, 0, 0, 0)]
    walk = [F(wolf(bob=(1 if i in (1, 4) else 0), legs=pat[i], lifts=lift[i], tail=i % 2)) for i in range(6)]
    attack = [
        F(wolf(dx=-1, drop=1, head_dy=1, legs=(-1, -1, 1, 1), leg_len=6)),
        F(wolf(dx=0, bob=-1, legs=(-2, -2, 2, 2), lifts=(1, 1, 0, 0), open_mouth=True, tail=1)),
        F(wolf(dx=1, bob=0, legs=(-2, -1, 2, 1), open_mouth=True, head_dy=1, tail=1)),
        F(wolf(dx=1, legs=(-1, -1, 1, 1), head_dy=1)),
        F(wolf(dx=0)),
    ]
    hurt = [F(flash(wolf(dx=-1, head_dy=-1))), F(wolf(dx=-1, head_dy=-1))]
    death = [
        F(flash(wolf(dx=-1, head_dy=-1))),
        F(wolf(drop=1, leg_len=6, head_dy=1)),
        F(wolf(drop=2, leg_len=5, head_dy=2, legs=(-1, -1, 1, 1))),
        F(wolf(drop=3, leg_len=4, head_dy=3, legs=(-2, -1, 2, 1), eye_closed=True)),
        F(wolf(drop=4, leg_len=3, head_dy=4, legs=(-2, -2, 2, 2), eye_closed=True)),
        F(wolf(drop=4, leg_len=3, head_dy=5, legs=(-3, -2, 3, 2), eye_closed=True, tail=-1)),
    ]
    return build_sheet([idle, walk, attack, hurt, death], 24, 24)


# ======================================================================================
# SKELETON ARCHER 24x24 (bone, dark sockets, bow + quiver)
# ======================================================================================
SKULL = [
    ".zzzz.",
    "zWWzzz",
    "zWzkzk",
    "zzzkzk",
    ".yzzzz",
    "..zyzy",
]
RIBS = [
    "..yzz",
    ".y...",
    ".yzzz",
    ".y...",
    ".yzz.",
    "..y..",
]


def draw_bow(c: Canvas, x: int, y: int, draw: int, arrow: bool, tilt: int = 0) -> None:
    """Vertical bow at column x (grip at y), string pulled back by `draw` pixels."""
    pts = [(-1, -6), (0, -5), (1, -4), (1, -3), (2, -2), (2, -1), (2, 0), (2, 1), (2, 2), (1, 3), (1, 4), (0, 5), (-1, 6)]
    for (dx, dy) in pts:
        c.set(x + dx + (tilt * dy) // 6, y + dy, "c")
    c.set(x - 1 + (tilt * -6) // 6, y - 6, "d")
    c.set(x + 2, y - 1, "b")
    c.set(x + 2, y, "b")
    # string
    top = (x - 1 + (tilt * -6) // 6, y - 6)
    bot = (x - 1 + (tilt * 6) // 6, y + 6)
    mid = (x - 1 - draw, y)
    c.line(*top, *mid, "z")
    c.line(*mid, *bot, "z")
    if arrow:
        c.line(mid[0], y, x + 4, y, "c")
        c.set(x + 5, y, "p")
        c.set(x + 4, y - 1, "p")
        c.set(x + 4, y + 1, "n")
        c.set(mid[0] - 1, y - 1, "S")
        c.set(mid[0] - 1, y + 1, "S")


def skeleton(bob: int = 0, ldx: int = 0, rdx: int = 0, llift: int = 0, rlift: int = 0, lean: int = 0,
             bow_y: int = 15, draw: int = 0, arrow: bool = False, bow_x: int = 17, crouch: int = 0,
             hand_back: tuple[int, int] | None = None) -> Canvas:
    c = Canvas(24, 24)
    ub = bob + crouch
    # quiver on the back
    c.rect(6 + lean, 10 + ub, 2, 6, "b")
    c.set(6 + lean, 10 + ub, "c")
    c.set(5 + lean, 8 + ub, "S")
    c.set(6 + lean, 9 + ub, "z")
    c.set(7 + lean, 8 + ub, "S")
    c.set(8 + lean, 9 + ub, "z")
    # far leg
    lx = 10 + ldx
    c.line(lx, 18 - llift, lx, 21 - llift, "y")
    c.set(lx + 1, 22 - llift, "y")
    c.set(lx, 22 - llift, "y")
    # pelvis + spine + ribs
    c.rect(10 + lean, 17 + ub, 4, 1, "z")
    c.set(10 + lean, 18 + ub, "y")
    c.set(13 + lean, 18 + ub, "y")
    c.stamp(RIBS, 9 + lean, 11 + ub)
    c.line(12 + lean, 15 + ub, 12 + lean, 17 + ub, "y")
    # near leg
    rx = 12 + rdx
    c.line(rx, 18 - rlift, rx, 21 - rlift, "z")
    c.set(rx, 22 - rlift, "z")
    c.set(rx + 1, 22 - rlift, "z")
    c.set(rx + 2, 22 - rlift, "y")
    # skull
    c.stamp(SKULL, 9 + lean, 5 + ub)
    # bow arm (front) to bow grip
    gy = bow_y + ub
    gx = bow_x + lean
    c.line(12 + lean, 12 + ub, gx, gy, "z")
    draw_bow(c, gx, gy, draw, arrow)
    # drawing arm
    hb = hand_back or (13 + lean, 15 + ub)
    if draw:
        hb = (gx - 1 - draw, gy)
    c.line(11 + lean, 12 + ub, hb[0], hb[1], "y")
    c.set(hb[0], hb[1], "z")
    return c


def skeleton_sheet() -> Canvas:
    F = finish
    idle = [F(skeleton(bob=b)) for b in (0, 0, 1, 1)]
    walk = []
    for f in range(6):
        p = f / 6 * 2 * math.pi
        s = math.sin(p)
        d = round(1.6 * s)
        walk.append(F(skeleton(bob=0 if abs(s) > 0.6 else 1, ldx=-d, rdx=d,
                               llift=1 if math.cos(p) < -0.5 else 0, rlift=1 if math.cos(p) > 0.5 else 0)))
    attack = [
        F(skeleton(bow_y=13, bow_x=18, arrow=True, draw=1)),
        F(skeleton(bow_y=13, bow_x=18, arrow=True, draw=4, lean=-1)),
        F(skeleton(bow_y=13, bow_x=18, draw=0, lean=0, hand_back=(10, 12))),
        F(skeleton(bow_y=14, bow_x=18, draw=0, hand_back=(11, 14))),
        F(skeleton(bow_y=15)),
    ]
    hurt = [F(flash(skeleton(lean=-1))), F(skeleton(lean=-1))]
    death = fall_frames(skeleton, dict(lean=-1), E_FOOT, 11, [-40, -75, -90, -90], 24, 24,
                        pre=[F(flash(skeleton(lean=-1))), F(skeleton(crouch=2, lean=-1))])
    return build_sheet([idle, walk, attack, hurt, death], 24, 24)


# ======================================================================================
# SLIME 24x24 (lake-blue jelly)
# ======================================================================================
def slime(rx: float = 7.5, ry: float = 6.0, lift: int = 0, dx: int = 0, eyes: bool = True,
          puddle: bool = False, open_mouth: bool = False) -> Canvas:
    c = Canvas(24, 24)
    base = E_FOOT + 1 - lift
    cy = base - ry
    c.shaded_ellipse(12 + dx, cy + 0.5, rx, ry + 0.5, "ABBC", bias=0.05, rim=True)
    # flatten the bottom
    for x in range(int(12 + dx - rx) + 1, int(12 + dx + rx)):
        if c.get(x, base - 1) is not None:
            c.set(x, base - 1, "A")
    # inner bubble + specular
    if not puddle:
        c.set(12 + dx - int(rx * 0.55), int(cy - ry * 0.45), "W")
        c.set(12 + dx - int(rx * 0.55) + 1, int(cy - ry * 0.45), "C")
        c.set(12 + dx - int(rx * 0.55), int(cy - ry * 0.45) + 1, "C")
        c.set(12 + dx - 2, int(cy + ry * 0.4), "C")
    if eyes:
        ey = int(cy - ry * 0.05)
        ex = 12 + dx + int(rx * 0.25)
        for ox in (0, 3):
            c.set(ex + ox, ey, "o")
            c.set(ex + ox, ey + 1, "o")
            c.set(ex + ox, ey - 1, "W" if ox == 0 else "C")
        if open_mouth:
            c.set(ex + 1, ey + 3, "o")
            c.set(ex + 2, ey + 3, "o")
    return c


def slime_sheet() -> Canvas:
    F = finish
    idle = [F(slime(7.5, 6.0)), F(slime(7.8, 5.7)), F(slime(8.0, 5.5)), F(slime(7.7, 5.8))]
    walk = [F(slime(8.4, 5.0)), F(slime(6.8, 6.8, lift=1, dx=1)), F(slime(6.6, 7.0, lift=3, dx=1)),
            F(slime(7.0, 6.5, lift=2, dx=2)), F(slime(8.6, 4.8, dx=2)), F(slime(7.8, 5.6, dx=1))]
    attack = [F(slime(8.6, 4.6, dx=-1)), F(slime(6.4, 7.4, lift=1, dx=1, open_mouth=True)),
              F(slime(8.0, 5.8, dx=3, open_mouth=True)), F(slime(8.6, 5.0, dx=2)), F(slime(7.6, 5.9, dx=1))]
    hurt = [F(flash(slime(8.2, 5.2, dx=-1))), F(slime(8.0, 5.4, dx=-1))]
    death = [F(flash(slime(8.6, 5.0))), F(slime(9.0, 4.4)), F(slime(9.6, 3.6, eyes=False)),
             F(slime(10.4, 2.6, eyes=False, puddle=True)), F(slime(10.8, 1.8, eyes=False, puddle=True)),
             F(slime(11.0, 1.4, eyes=False, puddle=True))]
    return build_sheet([idle, walk, attack, hurt, death], 24, 24)


# ======================================================================================
# FOREST GUARDIAN 64x64 (tree giant boss)
# ======================================================================================
B_FOOT = 62


def bark_column_colour(x: int, x0: int, x1: int) -> str:
    t = (x - x0) / max(1, x1 - x0)
    if t < 0.22:
        return "c"
    if t < 0.6:
        return "b"
    return "a"


def draw_bark(c: Canvas, x0: int, y0: int, x1: int, y1: int, seed: int) -> None:
    rnd = random.Random(seed)
    for x in range(x0, x1 + 1):
        col = bark_column_colour(x, x0, x1)
        for y in range(y0, y1 + 1):
            c.set(x, y, col)
    # vertical cracks
    for _ in range((x1 - x0) // 3):
        x = rnd.randint(x0 + 1, x1 - 1)
        y = rnd.randint(y0, y1 - 3)
        ln = rnd.randint(2, 5)
        for k in range(ln):
            c.set(x, y + k, "k")
            if c.get(x - 1, y + k) not in (None, "k"):
                c.set(x - 1, y + k, "d" if x < (x0 + x1) // 2 else "c")


def draw_limb(c: Canvas, x0: float, y0: float, x1: float, y1: float, r0: float, r1: float, ramp: str = "abc") -> None:
    steps = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1
    for i in range(steps + 1):
        t = i / steps
        x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        r = r0 + (r1 - r0) * t
        c.shaded_ellipse(x, y, r, r, ramp)


def trunk_halfwidth(y: int) -> float:
    if y < 36:
        return 11.5
    if y < 44:
        return 11.5 - (y - 36) * 0.3
    return 9.1 + (y - 44) * 0.3


def draw_fist(c: Canvas, x: float, y: float, r: float, down: bool = True) -> None:
    c.shaded_ellipse(x, y, r, r * 0.9, "abcd")
    if down:  # root fingers
        for k, dx in enumerate((-2, 0, 2)):
            c.line(x + dx, y + r * 0.6, x + dx + (k - 1) * 0.6, y + r + 1.5, "b")
            c.set(x + dx - 1, y + r * 0.6, "c")
    c.set(x - r * 0.4, y - r * 0.5, "j")


def guardian(bob: int = 0, arm: str = "rest", lean: int = 0, crouch: int = 0, sway: int = 0,
             fx: str | None = None, eyes: str = "x", legs: tuple[int, int] = (0, 0), lifts=(0, 0)) -> Canvas:
    c = Canvas(64, 64)
    ub = bob + crouch
    L = lean
    cx = 32 + L
    # legs: root stumps
    for i, (x, col) in enumerate(((23, "dark"), (35, "near"))):
        lx = x + legs[i]
        ly = 50 - lifts[i] + max(0, crouch - 1)
        ramp = "kab" if col == "dark" else "abc"
        c.shaded_ellipse(lx + 3.5, ly + 5, 4.4, 7.0, ramp)
        bot = B_FOOT - lifts[i]
        c.rect(lx - 1, bot - 1, 10, 2, ramp[1])
        c.rect(lx, bot, 9, 1, ramp[0])
        c.set(lx - 2, bot, ramp[0])
        c.set(lx + 9, bot, ramp[0])
        c.set(lx + 2, bot - 1, ramp[0])
        c.set(lx + 6, bot - 1, ramp[0])
    # back arm
    back = {"rest": ((21, 31), (15, 46)), "up1": ((21, 31), (14, 20)), "up2": ((22, 30), (22, 12)),
            "slam": ((24, 32), (40, 52))}[arm]
    (ax, ay), (bx, by) = back
    draw_limb(c, ax + L, ay + ub, bx + L, by + ub, 3.0, 3.4, "kab")
    c.shaded_ellipse(bx + L, by + ub + 2, 3.8, 3.4, "kab")
    # antler branches behind the crown
    for (x0, y0, x1, y1) in ((26, 14, 17, 3), (21, 8, 14, 7), (38, 14, 47, 3), (43, 8, 51, 6)):
        c.line(x0 + L + sway, y0 + ub, x1 + L + sway, y1 + ub, "b")
        c.line(x0 + L + sway + 1, y0 + ub, x1 + L + sway + 1, y1 + ub, "c")
    # trunk body (tapered: broad shoulders, narrow waist, root hips)
    rnd = random.Random(7)
    for y in range(25, 53):
        hw = trunk_halfwidth(y)
        x0, x1 = int(cx - hw), int(cx + hw)
        for x in range(x0, x1 + 1):
            t = (x - x0) / max(1, x1 - x0)
            col = "c" if t < 0.25 else ("b" if t < 0.66 else "a")
            if y == 25 and (x in (x0, x1)):
                continue
            c.set(x, y + ub, col)
    for (gx, gy, gl) in ((-8, 41, 6), (-5, 46, 5), (-1, 42, 4), (3, 44, 6), (7, 40, 5), (9, 47, 4)):
        x = cx + gx
        for k in range(gl):
            col = c.get(x, gy + k + ub)
            if col is not None:
                c.set(x, gy + k + ub, DARKER[col])
    # moss patches
    for (x, y, r) in ((cx - 8, 47, 2.0), (cx + 6, 50, 1.6), (cx - 4, 44, 1.2)):
        c.shaded_ellipse(x, y + ub, r + 0.6, r * 0.7, "uvw")
    # face: deep sockets with spore-glow eyes, jagged maw
    for ex in (cx - 6, cx + 2):
        c.rect(ex, 31 + ub, 4, 3, "k")
        c.set(ex, 31 + ub, "a")
        if eyes == "x":
            c.rect(ex + 1, 32 + ub, 2, 1, "x")
            c.set(ex + 2, 32 + ub, "W")
            c.set(ex + 1, 33 + ub, "w")
        else:
            c.rect(ex + 1, 32 + ub, 2, 1, eyes)
    c.line(cx - 8, 29 + ub, cx - 2, 31 + ub, "a")
    c.line(cx + 1, 31 + ub, cx + 7, 29 + ub, "a")
    c.line(cx - 7, 29 + ub, cx - 3, 30 + ub, "d")
    c.rect(cx - 4, 37 + ub, 8, 3, "k")
    for k, x in enumerate(range(cx - 4, cx + 4)):
        c.set(x, 37 + ub + (k % 2), "c" if k % 2 == 0 else "k")
        c.set(x, 40 + ub - (k % 2), "a")
    c.set(cx - 1, 38 + ub, "t")
    # crown: big leaf clumps, darker underneath, bumpy edge
    clumps = [(22, 6, 5, 4), (42, 6, 5, 4), (32, 6, 7, 5.5), (14, 15, 5.5, 5), (50, 15, 5.5, 5),
              (24, 13, 7.5, 6), (40, 13, 7.5, 6), (32, 14, 7, 5.5), (18, 21, 6.5, 4.5), (46, 21, 6.5, 4.5),
              (27, 21, 6.5, 4.5), (37, 21, 6.5, 4.5)]
    for (x, y, rx, ry) in clumps:
        clump(c, x + L + sway, y + ub, rx, ry, "w", "v", "u", rim=1.8)
    # glowing spore pods
    for (x, y) in ((26, 12), (38, 7), (45, 17), (20, 21)):
        c.set(x + L + sway, y + ub, "x")
        c.set(x + L + sway + 1, y + ub, "W")
        c.set(x + L + sway, y + ub + 1, "w")
    # front arm (drawn last)
    front = {"rest": ((44, 31), (50, 45), (51, 49)), "up1": ((44, 31), (49, 19), (49, 15)),
             "up2": ((42, 30), (43, 12), (43, 7)), "slam": ((44, 32), (53, 50), (55, 55))}[arm]
    (ax, ay), (bx, by), (fx_, fy_) = front
    draw_limb(c, ax + L, ay + ub, bx + L, by + ub, 3.6, 4.0)
    c.set(ax + L - 1, ay + ub + 3, "d")
    c.shaded_ellipse(ax + L, ay + ub - 1, 4.0, 2.6, "uvw")  # mossy shoulder
    draw_fist(c, fx_ + L, fy_ + ub, 4.6, down=arm in ("rest", "slam"))
    if fx == "slam":
        for (x, y, col) in ((46, 62, "d"), (48, 60, "c"), (62, 61, "d"), (63, 58, "c"), (44, 59, "w"),
                            (61, 54, "x"), (47, 56, "x"), (59, 62, "c"), (42, 62, "c"), (63, 62, "d")):
            c.set(x, y, col)
    return c


def guardian_sheet() -> Canvas:
    F = finish
    idle = [F(guardian(bob=b, sway=s)) for b, s in ((0, 0), (0, 1), (1, 1), (1, 0))]
    walk = []
    for f in range(6):
        p = f / 6 * 2 * math.pi
        s = math.sin(p)
        d = round(2 * s)
        walk.append(F(guardian(bob=0 if abs(s) > 0.6 else 1, legs=(-d, d),
                               lifts=(1 if math.cos(p) < -0.5 else 0, 1 if math.cos(p) > 0.5 else 0),
                               sway=-d // 2)))
    attack = [
        F(guardian(arm="up1", bob=-1, lean=-1)),
        F(guardian(arm="up2", bob=-2, lean=-2, sway=-1)),
        F(guardian(arm="slam", crouch=2, lean=2, sway=1, fx="slam")),
        F(guardian(arm="slam", crouch=2, lean=2, sway=1)),
        F(guardian(arm="rest", crouch=1)),
    ]
    hurt = [F(flash(guardian(lean=-1, sway=-1))), F(guardian(lean=-1, sway=-1))]
    withered = {"x": "w", "w": "v", "v": "u", "u": "t", "W": "w"}
    death = fall_frames(guardian, dict(eyes="k", lean=-1), B_FOOT, 32, [-30, -60, -90, -90], 64, 64,
                        last_remap=withered,
                        pre=[F(flash(guardian(lean=-1))), F(guardian(crouch=3, sway=-1, eyes="w"))])
    return build_sheet([idle, walk, attack, hurt, death], 64, 64)


# ======================================================================================
# Hero weapons: staff, crystal, cross, longbow, knife (used by the v3 hero rig below)
# ======================================================================================
def staff_end(hx: float, hy: float, ang: float, up: float) -> tuple[int, int]:
    t = math.radians(ang)
    return round(hx + math.cos(t) * up), round(hy + math.sin(t) * up)


def draw_staff(c: Canvas, hx: float, hy: float, ang: float, up: float, down: float,
               shaft: str = "c", hi: str = "d") -> tuple[int, int]:
    t = math.radians(ang)
    dx, dy = math.cos(t), math.sin(t)
    c.line(hx - dx * down, hy - dy * down, hx + dx * up, hy + dy * up, shaft)
    for k in (2, 5):  # lit knots on the upper part of the shaft
        c.set(round(hx + dx * (up - k)), round(hy + dy * (up - k)), hi)
    return staff_end(hx, hy, ang, up)


def draw_crystal(c: Canvas, x: int, y: int, glow: int = 0) -> None:
    """Blue crystal in a gold claw, centre (x, y)."""
    for (dx, dy, col) in ((0, -2, "C"), (-1, -1, "C"), (0, -1, "W"), (1, -1, "B"), (-1, 0, "B"), (0, 0, "C"),
                          (1, 0, "A"), (-1, 1, "B"), (0, 1, "B"), (1, 1, "A"), (0, 2, "A"),
                          (-2, 1, "r"), (2, 1, "q"), (-2, 0, "s"), (2, 0, "r"), (-1, 3, "q"), (1, 3, "q"), (0, 3, "r")):
        c.set(x + dx, y + dy, col)
    if glow >= 1:
        for (dx, dy, col) in ((0, -4, "N"), (-3, -2, "N"), (3, -2, "N"), (-4, 1, "M"), (4, 1, "M")):
            c.set(x + dx, y + dy, col)
    if glow >= 2:
        c.set(x, y - 1, "W")
        c.set(x, y, "W")
        for (dx, dy, col) in ((0, -5, "W"), (-4, -3, "C"), (4, -3, "C"), (-2, -5, "N"), (2, -5, "N"),
                              (-5, 0, "N"), (5, 0, "N")):
            c.set(x + dx, y + dy, col)


def draw_cross(c: Canvas, x: int, y: int, glow: int = 0) -> None:
    """Green cross in a gold ring, centre (x, y)."""
    for (dx, dy, col) in ((0, -2, "x"), (-1, -1, "r"), (0, -1, "x"), (1, -1, "q"), (-2, 0, "x"), (-1, 0, "x"),
                          (0, 0, "W"), (1, 0, "w"), (2, 0, "w"), (-1, 1, "r"), (0, 1, "w"), (1, 1, "q"),
                          (0, 2, "v"), (0, 3, "r")):
        c.set(x + dx, y + dy, col)
    if glow >= 1:
        for (dx, dy, col) in ((0, -4, "s"), (-3, -2, "x"), (3, -2, "x"), (-4, 1, "s"), (4, 1, "s")):
            c.set(x + dx, y + dy, col)
    if glow >= 2:
        c.set(x, y - 1, "W")
        c.set(x - 1, y, "W")
        for (dx, dy, col) in ((0, -5, "W"), (-4, -3, "W"), (4, -3, "W"), (-2, -5, "s"), (2, -5, "s"),
                              (-5, 0, "x"), (5, 0, "x")):
            c.set(x + dx, y + dy, col)


def draw_longbow(c: Canvas, gx: float, gy: float, tilt: float, draw: float, arrow: bool,
                 half: float = 8.0, bend: float = 3.0) -> tuple[int, int]:
    """Recurve bow gripped at (gx, gy); tilt = aim angle in degrees (0 = right, negative = up).
    Returns the string nock point (where the drawing hand is)."""
    t = math.radians(tilt)
    fx, fy = math.cos(t), math.sin(t)  # aim direction
    ax, ay = -fy, fx  # bow axis (points down for tilt 0)
    pts = []
    n = 24
    for i in range(n + 1):
        s = -1 + 2 * i / n
        f = bend * (1 - s * s) - 0.8 * max(0.0, abs(s) - 0.75) * 4  # recurved tips
        pts.append((gx + ax * s * half + fx * (f - bend), gy + ay * s * half + fy * (f - bend)))
    tip0, tip1 = pts[0], pts[-1]
    nock = (gx - fx * (bend + draw), gy - fy * (bend + draw))
    nock = (round(nock[0]), round(nock[1]))
    c.line(tip0[0], tip0[1], nock[0], nock[1], "z")
    c.line(nock[0], nock[1], tip1[0], tip1[1], "z")
    for i, (x, y) in enumerate(pts):
        c.set(x, y, "d" if i < n * 0.4 else "c")
    c.set(gx, gy, "a")
    if arrow:
        hx, hy = gx + fx * 3, gy + fy * 3
        c.line(nock[0], nock[1], hx, hy, "c")
        c.set(round(hx + fx), round(hy + fy), "W")
        c.set(round(hx), round(hy), "p")
        c.set(round(nock[0] - fx + ax), round(nock[1] - fy + ay), "S")
        c.set(round(nock[0] - fx - ax), round(nock[1] - fy - ay), "S")
    return nock


def draw_knife(c: Canvas, hx: float, hy: float, ang: float, blade: int = 4) -> None:
    t = math.radians(ang)
    dx, dy = math.cos(t), math.sin(t)
    px_, py_ = -dy, dx
    c.set(round(hx - dx * 2), round(hy - dy * 2), "r")
    c.set(round(hx - dx), round(hy - dy), "b")
    c.set(round(hx + dx + px_), round(hy + dy + py_), "q")
    c.set(round(hx + dx - px_), round(hy + dy - py_), "q")
    for i in range(1, blade + 1):
        c.set(round(hx + dx * (i + 1)), round(hy + dy * (i + 1)), "W" if i == blade else ("p" if i % 2 else "z"))


# ======================================================================================
# HEROES v3 (32x32): true 3/4 top-down view, new poses (style v2, docs/art/ART_BRIEF.md 1a)
# The camera looks down at ~45 deg: the top of the head and the shoulders are visible, the
# body is short ("toy" proportions, head ~1/3 of the height), feet a little apart, and every
# horizontal ring (belt, hem, collar) curves down in the middle because its near side faces
# the camera. One facing (right); the game mirrors for left.
#
# Shared rig: legs (or robe) + torso + head map + arms, posed by a dict (see hpose()).
# Drawing space: ground row G3 = 30; build_sheet lifts every frame by 1 so the feet land on
# y=29 and the outline under them on y=30 (1 px margin). The rig keeps at least one foot on
# the ground row in every standing frame, so the pivot never jitters.
#
# Head-map keys (remapped per class): 1 2 3 hair dark/mid/light, 4 5 6 skin shadow/mid/light,
# 7 8 beard dark/mid, 9 eye. Everything else in a map is a palette key.
# ======================================================================================
G3 = 30
CX = 15  # body axis (columns 15|16)


def hpose(**kw) -> dict:
    p = dict(ub=0, lean=0, hdx=0, hdy=0, near=(0, 0), far=(0, 0), kneel=False, swing=0, cloth=0,
             eyes="open", glow=0, fx=None)
    p.update(kw)
    return p


def head_v3(c: Canvas, art: list[str], x: int, y: int, hair: str, skin: str = "hij",
            beard: str = "ab", eyes: str = "open") -> None:
    eye = {"open": "o", "blink": skin[0], "pain": "o"}[eyes]
    remap = {"1": hair[0], "2": hair[1], "3": hair[2], "4": skin[0], "5": skin[1], "6": skin[2],
             "7": beard[0], "8": beard[1], "9": eye}
    c.stamp(art, x, y, remap=remap)
    if eyes == "pain":  # squeezed eyes: short dark dashes
        for j, row in enumerate(art):
            for i, ch in enumerate(row):
                if ch == "9":
                    c.set(x + i, y + j, skin[0])
                    c.set(x + i, y + j - 1, "a")


def shade_row(c: Canvas, y: int, x0: int, x1: int, ramp: str, lit_top: bool = False) -> None:
    """ramp = dark, mid, lit. Lit on the left (light from top-left), dark on the right."""
    for x in range(x0, x1 + 1):
        u = (x - x0) / max(1, x1 - x0)
        if lit_top:
            col = ramp[2] if u < 0.75 else ramp[1]
        else:
            col = ramp[2] if u < 0.25 else (ramp[1] if u < 0.74 else ramp[0])
        c.set(x, y, col)


def block_v3(c: Canvas, cx: int, top: int, spans: list[tuple[int, int]], ramp: str,
             lit_rows: int = 1) -> dict[int, tuple[int, int]]:
    """Torso-like block: spans = (left, right) offsets from cx per row, top rows lit (seen from above)."""
    rows = {}
    for i, (l, r) in enumerate(spans):
        y = top + i
        shade_row(c, y, cx + l, cx + r, ramp, lit_top=i < lit_rows)
        rows[y] = (cx + l, cx + r)
    return rows


def ring_v3(c: Canvas, y: int, x0: int, x1: int, cols: str, sag: float = 1.0, thick: int = 1) -> None:
    """Horizontal ring around the body seen from above: the middle (near side) sags down.
    cols = lit, mid, dark."""
    for x in range(x0, x1 + 1):
        u = (x - x0) / max(1, x1 - x0)
        dy = round(sag * math.sin(math.pi * u))
        col = cols[0] if u < 0.25 else (cols[1] if u < 0.75 else cols[2])
        for t in range(thick):
            c.set(x, y + dy + t, col)


def leg_v3(c: Canvas, hip_x: int, hip_y: int, dx: int, lift: int, pants: str, boot: str) -> None:
    """3-px leg from the hip to a boot on the ground row (toe points right). ramps dark, mid, lit."""
    gy = G3 - lift
    top_boot = gy - 2
    n = max(1, top_boot - hip_y)
    for y in range(hip_y, top_boot):
        x = round(hip_x + dx * (y - hip_y) / n)
        c.set(x, y, pants[2])
        c.set(x + 1, y, pants[1])
        c.set(x + 2, y, pants[0])
    fx = hip_x + dx
    c.set(fx, top_boot, boot[2])
    c.set(fx + 1, top_boot, boot[2])
    c.set(fx + 2, top_boot, boot[1])
    c.set(fx, top_boot + 1, boot[2])
    c.set(fx + 1, top_boot + 1, boot[1])
    c.set(fx + 2, top_boot + 1, boot[1])
    c.set(fx + 3, top_boot + 1, boot[1])
    for k in range(4):
        c.set(fx + k, gy, boot[0])


def legs_v3(c: Canvas, p: dict, pants: str, boot: str, hip_y: int = 22) -> None:
    """Far leg (one tone darker) then near leg. Hips 4 px apart so the feet stand apart."""
    dk = lambda r: "".join(DARKER[ch] for ch in r)
    if p["kneel"]:
        kneel_legs(c, pants, boot)
        return
    leg_v3(c, 12, hip_y, p["far"][0], p["far"][1], dk(pants), dk(boot))
    leg_v3(c, 16, hip_y, p["near"][0], p["near"][1], pants, boot)


def kneel_legs(c: Canvas, pants: str, boot: str) -> None:
    """Down on the far knee: far shin flat on the ground behind, near knee up in front."""
    dk = lambda r: "".join(DARKER[ch] for ch in r)
    fp, fb = dk(pants), dk(boot)
    # far leg: thigh down to the knee on the ground, shin + boot lying back along the ground
    for y in range(25, 30):
        c.set(12, y, fp[2])
        c.set(13, y, fp[1])
        c.set(14, y, fp[0])
    c.rect(8, 29, 6, 2, fp[1])
    c.rect(8, 29, 6, 1, fp[2])
    c.rect(6, 29, 2, 2, fb[1])
    c.set(6, 29, fb[2])
    # near leg: thigh forward to the knee, shin down to the planted boot
    for x in range(16, 21):
        c.set(x, 25, pants[2])
        c.set(x, 26, pants[1])
        c.set(x, 27, pants[0])
    c.set(20, 24, pants[2])
    c.set(21, 25, pants[1])
    for y in range(27, 30):
        c.set(19, y, pants[2])
        c.set(20, y, pants[1])
        c.set(21, y, pants[0])
    c.rect(19, 28, 4, 1, boot[1])
    c.set(19, 28, boot[2])
    c.rect(19, 29, 4, 1, boot[1])
    c.rect(19, G3, 4, 1, boot[0])


def arm_v3(c: Canvas, sx: float, sy: float, hx: float, hy: float, sleeve: str, skin: str = "hij",
           cuff: str | None = None, thick: int = 2) -> None:
    """Chunky arm (2-3 px) from the shoulder to a 2x2 fist. sleeve = dark, mid, lit."""
    dx, dy = hx - sx, hy - sy
    steps = max(abs(round(dx)), abs(round(dy)), 1)
    vertical = abs(dy) >= abs(dx)
    for k in range(steps + 1):
        x = round(sx + dx * k / steps)
        y = round(sy + dy * k / steps)
        if vertical:
            c.set(x, y, sleeve[2])
            for t in range(1, thick):
                c.set(x + t, y, sleeve[1] if t < thick - 1 or thick == 2 else sleeve[0])
        else:
            c.set(x, y, sleeve[2])
            for t in range(1, thick):
                c.set(x, y + t, sleeve[1] if t < thick - 1 or thick == 2 else sleeve[0])
    if cuff:
        L = max(1.0, math.hypot(dx, dy))
        ux, uy = dx / L, dy / L
        bx, by = round(hx - ux * 1.5), round(hy - uy * 1.5)
        if vertical:
            for t in range(thick):
                c.set(bx + t, by, cuff)
        else:
            for t in range(thick):
                c.set(bx, by + t, cuff)
    fist(c, hx, hy, skin)


def fist(c: Canvas, hx: float, hy: float, skin: str = "hij") -> None:
    hx, hy = round(hx), round(hy)
    c.set(hx, hy, skin[2])
    c.set(hx + 1, hy, skin[1])
    c.set(hx, hy + 1, skin[1])
    c.set(hx + 1, hy + 1, skin[0])


def sparks(c: Canvas, pts: tuple, dx: int = 0, dy: int = 0) -> None:
    for (x, y, col) in pts:
        c.set(x + dx, y + dy, col)


def smear(c: Canvas, cx: float, cy: float, r: float, a0: float, a1: float, cols: str = "Wp") -> None:
    """Swing smear: a crescent of light pixels along the swing (attack release frames),
    thick in the middle and thin at both ends."""
    n = max(6, int(abs(a1 - a0) / 5))
    for i in range(n + 1):
        t = i / n
        a = math.radians(a0 + (a1 - a0) * t)
        w = 0.6 + 2.2 * math.sin(math.pi * t)
        k = 0.0
        while k <= w:
            col = cols[0] if k < 1.0 else cols[1]
            c.set(round(cx + math.cos(a) * (r - k)), round(cy + math.sin(a) * (r - k)), col)
            k += 0.5


# ---------------------------------------------------------------- lying body (death 4-5)
def lying_v3(c: Canvas, stage: int, hair: str, skin: str, torso: str, legs: str | None, boot: str,
             robe: str | None = None, sleeve: str | None = None, collar: str | None = None,
             hood: str | None = None, trim: str | None = None) -> None:
    """Hero lying on the back in 3/4: head on the left (fell backwards), feet to the right.
    Seen from above the chest faces up (lit), the near flank shows as a darker band.
    stage -1 = collapsing (shoulders and head still up, propped on the far arm),
    0 = just landed (head and far arm still up 1 px), 1 = final, at rest."""
    b = -1 if stage == 0 else 0
    sleeve = sleeve or torso
    dk = lambda r: "".join(DARKER[ch] for ch in r)
    # far arm lying along the far side of the body
    arm_v3(c, 13, 21 + b, 19, 21 + b, dk(sleeve), skin)
    # legs or robe (feet to the right, toes up)
    if robe:
        for x in range(19, 28):
            t = (x - 19) / 8
            y0 = round(23 - t * 1.2)
            y1 = round(29 + t * 0.6)
            for y in range(y0, min(G3, y1) + 1):
                v = (y - y0) / max(1, y1 - y0)
                c.set(x, y, robe[2] if v < 0.3 else (robe[1] if v < 0.75 else robe[0]))
        if trim:
            for y in range(22, 30):
                if c.get(27, y) is not None:
                    c.set(27, y, trim)
        c.rect(28, 22, 2, 2, dk(boot)[1])
        c.set(29, 21, dk(boot)[2])
        c.rect(28, 26, 2, 2, boot[1])
        c.set(29, 25, boot[2])
    else:
        fl, nl = dk(legs), legs
        c.rect(20, 23, 6, 3, fl[1])
        c.rect(20, 23, 6, 1, fl[2])
        c.rect(26, 21, 2, 5, dk(boot)[1])
        c.set(26, 21, dk(boot)[2])
        c.set(28, 22, dk(boot)[1])
        c.rect(20, 26, 6, 3, nl[1])
        c.rect(20, 26, 6, 1, nl[2])
        c.rect(20, 28, 6, 1, nl[0])
        c.rect(26, 24, 2, 5, boot[1])
        c.set(26, 24, boot[2])
        c.rect(28, 25, 1, 3, boot[0])
        c.rect(26, 29, 3, 1, boot[0])
    # torso: chest on top (lit), near flank darker
    for x in range(11, 21):
        u = (x - 11) / 9
        top = 22 if 0.1 < u < 0.9 else 23
        for y in range(top, 30):
            col = torso[2] if y < 25 else (torso[1] if y < 28 else torso[0])
            c.set(x, y, col)
    if collar:
        for y in range(21, 30):
            for x in (11, 12):
                if c.get(x, y) is not None or 22 <= y <= 28:
                    c.set(x, y, collar[1] if x == 12 else collar[2])
        c.set(12, 21, collar[2])
        c.set(12, 29, collar[0])
    # near arm along the body, hand on the ground
    arm_v3(c, 13, 28, 20, 29, sleeve, skin)
    # head: top of the head points left, the face looks up at the sky (eyes stacked, closed)
    remap = {"1": (hood or hair)[0], "2": (hood or hair)[1], "3": (hood or hair)[2],
             "4": skin[0], "5": skin[1], "6": skin[2]}
    if stage == -1:
        # shoulders still off the ground: chest block rising to the left, head above it
        arm_v3(c, 12, 19, 8, 28, dk(sleeve), skin)
        for x in range(9, 17):
            t = (16 - x) / 7
            top = round(22 - t * 4)
            for y in range(top, 30):
                col = torso[2] if y < top + 2 else (torso[1] if y < 27 else torso[0])
                c.set(x, y, col)
        if collar:
            for x in range(8, 13):
                c.set(x, round(22 - (16 - x) / 7 * 4) - 1, collar[2])
                c.set(x, round(22 - (16 - x) / 7 * 4), collar[1])
        c.stamp(LYING_HEAD, 1, 13, remap=remap)
    else:
        c.stamp(LYING_HEAD, 2, 21 + b, remap=remap)
    if hood:
        ox, oy = (1, 13) if stage == -1 else (2, 21 + b)
        for (x, y) in ((3, 1), (3, 2), (3, 3), (3, 4), (3, 5), (4, 6), (4, 0), (5, 6), (6, 6)):
            c.set(ox + x, oy + y, hood[3] if len(hood) > 3 else hood[2])


LYING_HEAD = [
    "..12233...",
    ".1233666..",
    "1223646665",
    "1223666665",
    "1223666665",
    "1223646665",
    ".122366655",
    "..1122555.",
]


# ---------------------------------------------------------------- WARRIOR
# blond hair tied back, beard, rust fur collar, brown leather jerkin, round dark shield, sword
WAR3_HEAD = [
    "...33322...",
    ".233333221.",
    "23333222211",
    "12322266665",
    "12246666665",
    "11256669695",
    "11256666655",
    ".1125788865",
    "..11578875.",
    "....5775...",
]
WAR3_JERKIN = "kab"
WAR3_PANTS = "kab"
WAR3_BOOT = "abc"
WAR3_SPANS = [(-5, 5), (-5, 5), (-5, 5), (-5, 5), (-5, 4), (-4, 4), (-4, 4), (-4, 4), (-4, 4), (-4, 4)]


def shield_v3(c: Canvas, cx: float, cy: float) -> None:
    """Round shield facing the viewer: steel rim lit top-left, dark wood, bronze boss, pale emblem."""
    c.ellipse(cx, cy, 4.7, 5.2, "m")
    c.ellipse(cx + 0.2, cy + 0.2, 3.7, 4.2, "a")
    for y in range(int(cy) - 5, int(cy) + 6):
        for x in range(int(cx) - 5, int(cx) + 6):
            if c.get(x, y) == "a" and (x + 0.5 - cx) + (y + 0.5 - cy) * 0.8 > 1.6:
                c.set(x, y, "k")
            if c.get(x, y) == "m" and (x + 0.5 - cx) + (y + 0.5 - cy) < -2.5:
                c.set(x, y, "n")
    cx, cy = round(cx - 0.5), round(cy - 0.5)
    for (dx, dy, col) in ((-2, -4, "p"), (-3, -3, "p"), (0, -3, "z"), (0, -2, "z"), (-2, 0, "z"), (2, 0, "y"),
                          (0, 2, "y"), (0, 3, "y"), (-1, 0, "q"), (1, 0, "q"), (0, -1, "q"), (0, 1, "q"),
                          (0, 0, "r"), (-1, -1, "s")):
        c.set(cx + dx, cy + dy, col)


def warrior_v3(p: dict, sword: float = 112, sword_len: int = 8, nh=None, fh=None, shield=True,
               sword_behind: bool = False) -> Canvas:
    c = Canvas(32, 32)
    ub, lx = p["ub"], p["lean"]
    legs_v3(c, p, WAR3_PANTS, WAR3_BOOT)
    if p["kneel"]:
        ub += 3
    nhx, nhy = nh if nh else (16 - p["swing"] // 2, 21)
    fhx, fhy = fh if fh else (22 + p["swing"] // 2, 19)
    nhx, nhy, fhx, fhy = nhx + lx, nhy + ub, fhx + lx, fhy + ub
    if sword_behind:
        draw_sword(c, nhx, nhy, sword, sword_len)
    # torso
    rows = block_v3(c, CX + lx, 13 + ub, WAR3_SPANS, WAR3_JERKIN, lit_rows=1)
    # cross strap (bronze studs) and belt ring
    for k in range(6):
        c.set(CX - 3 + lx + k, 15 + ub + k, "k" if k % 2 else "a")
    c.set(CX - 1 + lx, 17 + ub, "r")
    ring_v3(c, 20 + ub, CX - 4 + lx, CX + 4 + lx, "bak", sag=1.0)
    c.set(CX + 1 + lx, 21 + ub, "r")
    c.set(CX + 2 + lx, 21 + ub, "q")
    # fur collar around the shoulders (seen from above: a thick ring)
    for y in range(10, 18):
        for x in range(CX - 8, CX + 9):
            nx, ny = (x + 0.5 - (CX + 0.5)) / 6.7, (y + 0.5 - 14.2) / 3.0
            if nx * nx + ny * ny <= 1:
                col = "g" if (ny < -0.2 and nx < 0.3) else ("f" if nx < 0.55 else "e")
                if ny > 0.55:
                    col = "e" if nx > -0.4 else "f"
                c.set(x + lx, y + ub, col)
    for x in range(CX - 5, CX + 6):  # ragged fur edge
        if (x - CX) % 3 == 1:
            c.set(x + lx, 17 + ub, None)
        elif (x - CX) % 3 == 0:
            c.set(x + lx, 18 + ub, "f" if x < CX else "e")
    head_v3(c, WAR3_HEAD, 10 + lx + p["hdx"], 3 + ub + p["hdy"], "bcd", beard="cd", eyes=p["eyes"])
    if shield:
        shield_v3(c, fhx + 0.5, fhy + 0.5)
    if not sword_behind:
        draw_sword(c, nhx, nhy, sword, sword_len)
    arm_v3(c, CX + 3 + lx, 15 + ub, nhx, nhy, "hij", cuff="a")
    c.set(CX + 3 + lx, 15 + ub, "b")
    c.set(CX + 4 + lx, 15 + ub, "a")
    c.set(CX + 3 + lx, 14 + ub, "c")
    if p["fx"] == "slash":
        smear(c, CX + lx, 15 + ub, 11, -70, 40)
    if p["fx"] == "slam":
        sparks(c, ((22, 30, "W"), (29, 30, "W"), (21, 28, "z"), (30, 27, "z"), (20, 25, "W"), (31, 24, "W"),
                   (24, 27, "W"), (28, 26, "z")))
    return c


def warrior_lying(stage: int) -> Canvas:
    c = Canvas(32, 32)
    draw_sword(c, 15, 19, 5, 10)  # dropped sword behind the body
    lying_v3(c, stage, "bcd", "hij", WAR3_JERKIN, WAR3_PANTS, WAR3_BOOT, collar="efg")
    shield_v3(c, 24.5, 18.5 - (1 if stage == 0 else 0))
    return c


def warrior_sheet_v3() -> Canvas:
    F = finish
    W = warrior_v3
    idle = [F(W(hpose(ub=b, eyes="blink" if i == 3 else "open"))) for i, b in enumerate((0, 0, 1, 1))]
    walk = [F(W(p, sword=112 + p["swing"] * 5)) for p in walk_poses()]
    attack = [
        F(W(hpose(lean=-1, near=(1, 0), far=(-1, 0)), nh=(13, 13), sword=-150, sword_behind=True)),   # wind-up
        F(W(hpose(lean=-1, ub=-1, near=(1, 0), far=(-2, 0)), nh=(14, 9), sword=-115, sword_behind=True,
            fh=(19, 19))),
        F(W(hpose(lean=1, ub=1, near=(2, 0), far=(-2, 0), fx="slash"), nh=(22, 17), sword=15, sword_behind=False, sword_len=10,
            fh=(18, 20))),                                                                          # hit
        F(W(hpose(lean=1, ub=1, near=(2, 0), far=(-2, 0)), nh=(21, 21), sword=70, sword_behind=False, fh=(18, 20))),
        F(W(hpose(near=(1, 0), far=(-1, 0)), nh=(17, 21), sword=95)),
    ]
    hurt_p = hpose(lean=-1, hdx=-1, eyes="pain")
    hurt = [F(flash(W(hurt_p, nh=(17, 20), fh=(20, 18), sword=100, sword_behind=False))), F(W(hurt_p, nh=(17, 20), fh=(20, 18), sword=100, sword_behind=False))]
    death = [
        F(W(hpose(lean=-1, hdx=-1, hdy=-1, eyes="pain", far=(-2, 0)), nh=(16, 19), fh=(19, 17), sword=130, sword_behind=False)),
        F(W(hpose(kneel=True, eyes="pain"), nh=(19, 20), fh=(19, 19), sword=80, sword_behind=False)),
        F(W(hpose(kneel=True, ub=1, hdx=1, hdy=1, eyes="blink"), nh=(20, 22), fh=(17, 21), sword=10, sword_behind=False,
            shield=True)),
        F(warrior_lying(-1)),
        F(warrior_lying(0)),
        F(warrior_lying(1)),
    ]
    cast = [
        F(W(hpose(ub=0), nh=(21, 12), sword=-80, sword_behind=False, fh=(19, 21))),
        F(W(hpose(ub=-1, near=(1, 0), far=(-1, 0)), nh=(21, 9), sword=-85, sword_behind=False, fh=(19, 21))),
        F(W(hpose(ub=2, near=(2, 0), far=(-2, 0)), nh=(22, 19), sword=80, sword_behind=False, sword_len=9, fh=(17, 21))),
        F(W(hpose(ub=2, near=(2, 0), far=(-2, 0), fx="slam"), nh=(22, 19), sword=80, sword_behind=False, sword_len=9, fh=(17, 21))),
    ]
    return build_sheet([idle, walk, attack, hurt, death, cast], 32, 32)


def walk_poses() -> list[dict]:
    """6-frame walk: contact, down, passing (far leg lifted), contact, down, passing (near lifted).
    Body is 1 px lower on the 'down' frames; arms swing against the legs."""
    return [
        hpose(near=(2, 0), far=(-2, 0), swing=-2, cloth=0),
        hpose(near=(1, 0), far=(-1, 0), swing=-1, ub=1, cloth=1),
        hpose(near=(0, 0), far=(0, 1), swing=0, cloth=1),
        hpose(near=(-2, 0), far=(2, 0), swing=2, cloth=0),
        hpose(near=(-1, 0), far=(1, 0), swing=1, ub=1, cloth=1),
        hpose(near=(0, 1), far=(0, 0), swing=0, cloth=1),
    ]


# ---------------------------------------------------------------- robes (mage, healer)
def robe_v3(c: Canvas, p: dict, top: int, hw0: float, hw1: float, ramp: str, trim: str | None,
            boot: str = "kab", power: float = 1.3) -> dict[int, tuple[int, int]]:
    """Bell robe from the shoulders to the ground, lit left / dark right. The hem is a curve
    (near side lower) with a trim band; boot toes peek out under it and alternate in walk."""
    ub, lx = p["ub"], p["lean"]
    dk = "".join(DARKER[ch] for ch in boot)
    if p["kneel"]:
        top += 3
    # toes under the hem (far one darker), on the ground row
    nd, fd = p["near"][0], p["far"][0]
    for (bx, lift, b) in ((CX - 3 + fd, p["far"][1], dk), (CX + 1 + nd, p["near"][1], boot)):
        c.rect(bx, G3 - lift, 4, 1, b[1])
        c.set(bx + 3, G3 - lift, b[0])
        c.set(bx, G3 - 1 - lift, b[2])
        c.set(bx + 1, G3 - 1 - lift, b[1])
        c.set(bx + 2, G3 - 1 - lift, b[1])
    bottom = G3 - 1
    sway = (-1 if p["cloth"] else 0) + (nd - fd) * 0.25
    rows = {}
    for y in range(top + ub, bottom + 1):
        t = (y - top - ub) / max(1, bottom - top - ub)
        hw = hw0 + (hw1 - hw0) * t ** power
        mid = CX + 0.5 + lx * (1 - t) + sway * t
        x0, x1 = round(mid - hw), round(mid + hw) - 1
        if y == bottom:          # curved hem: corners lifted
            x0, x1 = x0 + 2, x1 - 2
        elif y == bottom - 1:
            x0, x1 = x0 + 1, x1 - 1
        shade_row(c, y, x0, x1, ramp, lit_top=(y == top + ub))
        rows[y] = (x0, x1)
    if trim:
        # trim follows the hem curve: lowest robe pixel + one above in each column
        cols: dict[int, int] = {}
        for y, (x0, x1) in rows.items():
            for x in range(x0, x1 + 1):
                cols[x] = max(cols.get(x, 0), y)
        xs = sorted(cols)
        for x in xs:
            u = (x - xs[0]) / max(1, xs[-1] - xs[0])
            col = trim[0] if u < 0.7 else trim[1]
            c.set(x, cols[x], col)
            c.set(x, cols[x] - 1, col if u < 0.7 else trim[1])
    return rows


# ---------------------------------------------------------------- MAGE
# long dark hair and beard, high violet collar, dark purple robe with gold trim, crystal staff
MAGE3_HEAD = [
    "...33322...",
    ".233333221.",
    "23333222211",
    "12322266665",
    "11246666665",
    "11156669695",
    "11156666655",
    "1111788887.",
    "111.788887.",
    ".1...7887..",
]
MAGE3_ROBE = "KLM"


def mage_v3(p: dict, nh=None, staff: float = -90, up: float = 15, down: float = 10, fh=None,
            far_up: bool = False) -> Canvas:
    c = Canvas(32, 32)
    ub, lx = p["ub"], p["lean"]
    if p["kneel"]:
        ub += 3
    nhx, nhy = nh if nh else (21 - p["swing"] // 2, 19)
    nhx, nhy = nhx + lx, nhy + ub
    rows = robe_v3(c, p, 13, 5.0, 7.8, MAGE3_ROBE, "rq")
    # front opening (gold edge) at the near-front of the robe
    for y in range(20 + ub, G3 - 1):
        if y in rows:
            x0, x1 = rows[y]
            ox = x0 + round((x1 - x0) * 0.62)
            c.set(ox, y, "r")
            c.set(ox + 1, y, "K")
    # belt + pouch
    yb = 19 + ub
    x0, x1 = rows[yb]
    ring_v3(c, yb, x0, x1, "bak", sag=1.0)
    c.set(CX + 1 + lx, yb + 1, "r")
    c.rect(x0 + 1, yb + 2, 2, 2, "b")
    c.set(x0 + 1, yb + 2, "c")
    # high collar ring around the neck (seen from above)
    for y in range(10, 17):
        for x in range(CX - 7, CX + 8):
            nx, ny = (x + 0.5 - (CX + 0.5)) / 6.2, (y + 0.5 - 13.8) / 2.9
            if nx * nx + ny * ny <= 1:
                col = "M" if (ny < 0 and nx < 0.2) else ("L" if nx < 0.6 else "K")
                if ny > 0.45:
                    col = "r" if nx < 0.5 else "q"
                c.set(x + lx, y + ub, col)
    if far_up and fh:  # raised far arm beside the head
        arm_v3(c, CX - 3 + lx, 14 + ub, fh[0] + lx, fh[1] + ub, "KLM", cuff="r", thick=3)
    head_v3(c, MAGE3_HEAD, 10 + lx + p["hdx"], 3 + ub + p["hdy"], "kab", beard="ka", eyes=p["eyes"])
    # beard falls over the chest
    for (x, y, col) in ((CX + 1, 13, "a"), (CX + 2, 13, "a"), (CX + 3, 13, "k"), (CX + 1, 14, "a"),
                        (CX + 2, 14, "k"), (CX + 2, 15, "k")):
        c.set(x + lx + p["hdx"], y + ub + p["hdy"], col)
    tx, ty = draw_staff(c, nhx, nhy, staff, up, down, shaft="b", hi="c")
    if fh and not far_up:
        arm_v3(c, CX - 1 + lx, 15 + ub, fh[0] + lx, fh[1] + ub, "KLM", cuff="r", thick=3)
    arm_v3(c, CX + 3 + lx, 15 + ub, nhx, nhy, "KMN", cuff="r", thick=3)
    draw_crystal(c, tx, ty, p["glow"])
    if p["fx"] == "spark":
        sparks(c, ((3, 0, "W"), (5, 0, "N"), (4, -2, "C"), (4, 2, "C"), (6, -1, "N")), tx, ty)
    if p["fx"] == "ground":
        sparks(c, ((5, 29, "N"), (8, 27, "C"), (25, 29, "N"), (28, 26, "C"), (11, 24, "W"), (27, 22, "W"),
                   (4, 25, "C"), (29, 29, "W")))
    return c


def mage_lying(stage: int) -> Canvas:
    c = Canvas(32, 32)
    draw_staff(c, 6, 18, -8, 18, 4, shaft="b", hi="c")
    draw_crystal(c, 24, 15 + (stage == 0), 0)
    lying_v3(c, stage, "kab", "hij", MAGE3_ROBE, None, "kab", robe=MAGE3_ROBE, trim="r", collar="KLM")
    for (x, y, col) in ((10, 25, "a"), (10, 26, "k"), (11, 26, "a"), (11, 27, "k"), (10, 24, "a")):
        c.set(x, y - (stage == 0), col)  # beard
    return c


def mage_sheet_v3() -> Canvas:
    F = finish
    M = mage_v3
    idle = [F(M(hpose(ub=b, cloth=(i in (1, 2)), eyes="blink" if i == 3 else "open"), up=15 - b))
            for i, b in enumerate((0, 0, 1, 1))]
    walk = [F(M(p, staff=-90 - p["swing"] * 2, up=15 - p["ub"])) for p in walk_poses()]
    attack = [
        F(M(hpose(lean=-1, glow=1), nh=(18, 18), staff=-125, up=12, down=8)),                     # draw back
        F(M(hpose(lean=-1, ub=-1, glow=1, near=(1, 0), far=(-1, 0)), nh=(17, 17), staff=-135, up=12, down=7)),
        F(M(hpose(lean=1, ub=1, glow=2, fx="spark", near=(2, 0), far=(-2, 0)), nh=(24, 17), staff=-35, up=8,
            down=8, fh=(22, 19))),                                                                # release
        F(M(hpose(lean=1, ub=1, glow=1, near=(2, 0), far=(-2, 0)), nh=(23, 18), staff=-45, up=9, down=8)),
        F(M(hpose(near=(1, 0), far=(-1, 0)), nh=(21, 19), staff=-80, up=14)),
    ]
    hurt_p = hpose(lean=-1, hdx=-1, eyes="pain")
    hurt = [F(flash(M(hurt_p, nh=(20, 19), staff=-105))), F(M(hurt_p, nh=(20, 19), staff=-105))]
    death = [
        F(M(hpose(lean=-1, hdx=-1, hdy=-1, eyes="pain"), nh=(19, 18), staff=-112)),
        F(M(hpose(kneel=True, eyes="pain"), nh=(21, 19), staff=-100, up=13)),
        F(M(hpose(kneel=True, ub=1, hdx=1, hdy=1, eyes="blink"), nh=(21, 21), staff=-60, up=13, down=4)),
        F(mage_lying(-1)),
        F(mage_lying(0)),
        F(mage_lying(1)),
    ]
    cast = [
        F(M(hpose(glow=1), nh=(20, 16), staff=-90, up=12, fh=(20, 20))),
        F(M(hpose(ub=-1, glow=2, cloth=1), nh=(20, 12), staff=-90, up=9, down=12, fh=(20, 16))),
        F(M(hpose(ub=-1, glow=2, cloth=1, fx="ground"), nh=(20, 12), staff=-90, up=9, down=12, fh=(20, 16))),
        F(M(hpose(glow=1), nh=(20, 16), staff=-90, up=12, fh=(20, 20))),
    ]
    return build_sheet([idle, walk, attack, hurt, death, cast], 32, 32)


# ---------------------------------------------------------------- HEALER
# dark curly hair, green hooded mantle on the shoulders, white robe with green panel, gold cross staff
HEAL3_HEAD = [
    "..333322...",
    ".23333322 1",
    "23333322221",
    "23322266662",
    "12246666662",
    "11256669695",
    "11256666651",
    "111256665 1",
    "1111.5555..",
    ".11........",
]
HEAL3_ROBE = "yzW"


def healer_v3(p: dict, nh=None, staff: float = -90, up: float = 14, down: float = 10, fh=None,
              far_up: bool = False) -> Canvas:
    c = Canvas(32, 32)
    ub, lx = p["ub"], p["lean"]
    if p["kneel"]:
        ub += 3
    nhx, nhy = nh if nh else (21 - p["swing"] // 2, 19)
    nhx, nhy = nhx + lx, nhy + ub
    rows = robe_v3(c, p, 14, 4.6, 7.2, HEAL3_ROBE, "vu", boot="abc")
    # green front panel with gold stitches
    for y in range(19 + ub, G3 - 1):
        if y in rows:
            x0, x1 = rows[y]
            ox = x0 + round((x1 - x0) * 0.56)
            c.set(ox, y, "v" if y % 3 else "r")
            c.set(ox + 1, y, "u")
    yb = 19 + ub
    x0, x1 = rows[yb]
    ring_v3(c, yb, x0, x1, "rrq", sag=1.0)
    c.rect(x0 + 1, yb + 2, 2, 2, "b")
    c.set(x0 + 1, yb + 2, "c")
    # green mantle over the shoulders + hood lying on the back (left)
    for y in range(9, 19):
        for x in range(CX - 8, CX + 8):
            nx, ny = (x + 0.5 - (CX + 0.2)) / 6.6, (y + 0.5 - 14.6) / 3.4
            if nx * nx + ny * ny <= 1:
                col = "w" if (ny < -0.1 and nx < 0.1) else ("v" if nx < 0.55 else "u")
                if ny > 0.5:
                    col = "u" if nx < 0.4 else "t"
                c.set(x + lx, y + ub, col)
    c.ellipse(CX - 4.5 + lx, 12.5 + ub, 2.6, 2.4, "u")   # hood bunched behind the neck
    c.set(CX - 6 + lx, 11 + ub, "v")
    c.set(CX - 5 + lx, 11 + ub, "v")
    c.set(CX + 1 + lx, 17 + ub, "r")  # gold clasp
    if far_up and fh:  # raised far arm beside the head
        arm_v3(c, CX - 5 + lx, 14 + ub, fh[0] + lx, fh[1] + ub, "yzW", cuff="v", thick=2)
    head_v3(c, HEAL3_HEAD, 10 + lx + p["hdx"], 3 + ub + p["hdy"], "abc", eyes=p["eyes"])
    tx, ty = draw_staff(c, nhx, nhy, staff, up, down, shaft="q", hi="r")
    if fh and not far_up:
        arm_v3(c, CX - 1 + lx, 15 + ub, fh[0] + lx, fh[1] + ub, "yzW", cuff="v", thick=2)
    arm_v3(c, CX + 3 + lx, 15 + ub, nhx, nhy, "yzW", cuff="v", thick=2)
    draw_cross(c, tx, ty, p["glow"])
    if p["fx"] == "spark":
        sparks(c, ((3, 0, "W"), (5, 0, "s"), (4, -2, "x"), (4, 2, "x"), (6, -1, "s")), tx, ty)
    if p["fx"] == "light":
        sparks(c, ((5, 8, "s"), (8, 3, "W"), (26, 4, "s"), (11, 1, "s"), (27, 10, "W"), (4, 14, "W"),
                   (6, 24, "x"), (27, 25, "x")))
    return c


def healer_lying(stage: int) -> Canvas:
    c = Canvas(32, 32)
    draw_staff(c, 7, 18, -6, 17, 4, shaft="q", hi="r")
    draw_cross(c, 24, 16 + (stage == 0), 0)
    lying_v3(c, stage, "abc", "hij", "tuv", None, "abc", robe=HEAL3_ROBE, trim="v", sleeve="yzW",
             collar="tuv")
    return c


def healer_sheet_v3() -> Canvas:
    F = finish
    H = healer_v3
    idle = [F(H(hpose(ub=b, cloth=(i in (1, 2)), eyes="blink" if i == 3 else "open"), up=14 - b))
            for i, b in enumerate((0, 0, 1, 1))]
    walk = [F(H(p, staff=-90 - p["swing"] * 2, up=14 - p["ub"])) for p in walk_poses()]
    attack = [
        F(H(hpose(lean=-1, glow=1), nh=(18, 18), staff=-125, up=12, down=8)),
        F(H(hpose(lean=-1, ub=-1, glow=1, near=(1, 0), far=(-1, 0)), nh=(17, 17), staff=-135, up=12, down=7)),
        F(H(hpose(lean=1, ub=1, glow=2, fx="spark", near=(2, 0), far=(-2, 0)), nh=(24, 17), staff=-30, up=7,
            down=8, fh=(22, 19))),
        F(H(hpose(lean=1, ub=1, glow=1, near=(2, 0), far=(-2, 0)), nh=(23, 18), staff=-40, up=8, down=8)),
        F(H(hpose(near=(1, 0), far=(-1, 0)), nh=(21, 19), staff=-80, up=13)),
    ]
    hurt_p = hpose(lean=-1, hdx=-1, eyes="pain")
    hurt = [F(flash(H(hurt_p, nh=(20, 19), staff=-105))), F(H(hurt_p, nh=(20, 19), staff=-105))]
    death = [
        F(H(hpose(lean=-1, hdx=-1, hdy=-1, eyes="pain"), nh=(19, 18), staff=-112)),
        F(H(hpose(kneel=True, eyes="pain"), nh=(21, 19), staff=-100, up=12)),
        F(H(hpose(kneel=True, ub=1, hdx=1, hdy=1, eyes="blink"), nh=(21, 21), staff=-60, up=12, down=4)),
        F(healer_lying(-1)),
        F(healer_lying(0)),
        F(healer_lying(1)),
    ]
    cast = [
        F(H(hpose(glow=1), nh=(20, 15), staff=-90, up=11, fh=(7, 10), far_up=True)),
        F(H(hpose(ub=-1, glow=2, cloth=1), nh=(20, 11), staff=-90, up=8, down=12, fh=(6, 6), far_up=True)),
        F(H(hpose(ub=-1, glow=2, cloth=1, fx="light"), nh=(20, 11), staff=-90, up=8, down=12, fh=(6, 6),
            far_up=True)),
        F(H(hpose(glow=1), nh=(20, 15), staff=-90, up=11, fh=(7, 11), far_up=True)),
    ]
    return build_sheet([idle, walk, attack, hurt, death, cast], 32, 32)


# ---------------------------------------------------------------- ARCHER
# short brown hair, green cowl + cloak, leather jerkin, quiver on the back, longbow in the far hand
ARCH3_HEAD = [
    "...33322...",
    ".233333221.",
    "23333322211",
    "12333222665",
    "12246666665",
    "11256669695",
    ".1256666655",
    "..12566655.",
    "...255555..",
    "....5555...",
]
ARCH3_JERKIN = "abc"
ARCH3_PANTS = "tuv"
ARCH3_BOOT = "abc"
ARCH3_SPANS = [(-4, 4), (-5, 4), (-5, 4), (-5, 4), (-4, 4), (-4, 4), (-4, 4), (-4, 4), (-4, 4), (-4, 4)]


def archer_v3(p: dict, grip=None, tilt: float = 0, draw: float = 0, arrow: bool = False, pull=None,
              fx: str | None = None) -> Canvas:
    c = Canvas(32, 32)
    ub, lx = p["ub"], p["lean"]
    if p["kneel"]:
        ub += 3
    # cloak hanging behind the back (left), flutters in walk
    fl = p["cloth"]
    for y in range(13 + ub, 27 + (0 if p["kneel"] else 0)):
        k = y - 13 - ub
        x0 = round(CX - 6 + lx - k * 0.3 - (fl if k > 6 else 0))
        for x in range(x0, CX + 1 + lx):
            c.set(x, y, "v" if x == x0 and k < 8 else ("u" if x < x0 + 3 else "t"))
    hem0 = round(CX - 6 + lx - (26 - 13) * 0.3 - fl)
    for i, x in enumerate(range(hem0, CX + 1 + lx)):
        if i % 3 != 2:
            c.set(x, 27, "t")
    # quiver on the back: tube across the far shoulder, fletchings above it
    c.line(CX - 4 + lx, 19 + ub, CX - 8 + lx, 9 + ub, "a")
    c.line(CX - 3 + lx, 19 + ub, CX - 7 + lx, 9 + ub, "b")
    c.line(CX - 2 + lx, 19 + ub, CX - 6 + lx, 9 + ub, "a")
    sparks(c, ((CX - 9, 6, "W"), (CX - 8, 5, "z"), (CX - 7, 6, "W"), (CX - 6, 5, "z"), (CX - 9, 7, "S"),
               (CX - 7, 7, "S"), (CX - 8, 8, "c"), (CX - 6, 8, "c"), (CX - 8, 7, "a")), lx, ub)
    legs_v3(c, p, ARCH3_PANTS, ARCH3_BOOT)
    block_v3(c, CX + lx, 13 + ub, ARCH3_SPANS, ARCH3_JERKIN, lit_rows=1)
    # laced front + belt
    for y in range(16, 20):
        c.set(CX + 2 + lx, y + ub, "a")
    ring_v3(c, 20 + ub, CX - 4 + lx, CX + 4 + lx, "kka", sag=1.0)
    c.set(CX + 1 + lx, 21 + ub, "r")
    # green cowl around the neck (seen from above)
    for y in range(10, 18):
        for x in range(CX - 8, CX + 8):
            nx, ny = (x + 0.5 - (CX + 0.2)) / 6.4, (y + 0.5 - 14.2) / 2.9
            if nx * nx + ny * ny <= 1:
                col = "w" if (ny < -0.1 and nx < 0.0) else ("v" if nx < 0.55 else "u")
                if ny > 0.5:
                    col = "u" if nx < 0.4 else "t"
                c.set(x + lx, y + ub, col)
    for x in range(CX - 4, CX + 5, 3):  # pointed cowl edge
        c.set(x + lx, 17 + ub + (1 if abs(x - CX) < 3 else 0), "u" if x < CX else "t")
    head_v3(c, ARCH3_HEAD, 10 + lx + p["hdx"], 3 + ub + p["hdy"], "abc", eyes=p["eyes"])
    # bow in the far hand in front of the body, string hand = near hand
    gx, gy = grip if grip else (23, 18)
    gx, gy = gx + lx, gy + ub
    nock = draw_longbow(c, gx, gy, tilt, draw, arrow)
    arm_v3(c, CX + 2 + lx, 15 + ub, gx - 1, gy, "abc", cuff="k")
    hand = nock if (draw or arrow) else ((pull[0] + lx, pull[1] + ub) if pull else (CX + 2 + lx, 21 + ub))
    arm_v3(c, CX + 3 + lx, 15 + ub, hand[0], hand[1], "abc", cuff="k")
    if fx == "release":
        t = math.radians(tilt)
        for k, col in ((4, "W"), (6, "z"), (8, "W"), (10, "z")):
            c.set(round(gx + math.cos(t) * k), round(gy + math.sin(t) * k), col)
    if fx == "volley":
        sparks(c, ((27, 6, "W"), (29, 9, "z"), (25, 3, "z"), (30, 4, "W"), (28, 2, "W")))
    return c


def archer_lying(stage: int) -> Canvas:
    c = Canvas(32, 32)
    draw_longbow(c, 16, 18, -90, 0, False)
    lying_v3(c, stage, "abc", "hij", ARCH3_JERKIN, ARCH3_PANTS, ARCH3_BOOT, collar="tuv")
    return c


def archer_sheet_v3() -> Canvas:
    F = finish
    A = archer_v3
    idle = [F(A(hpose(ub=b, cloth=(i in (1, 2)), eyes="blink" if i == 3 else "open"))) for i, b in
            enumerate((0, 0, 1, 1))]
    walk = [F(A(p, grip=(23 - p["swing"] // 2, 18), tilt=-p["swing"] * 3)) for p in walk_poses()]
    attack = [
        F(A(hpose(near=(1, 0), far=(-1, 0)), grip=(24, 16), arrow=True, draw=1)),          # nock
        F(A(hpose(lean=-1, near=(2, 0), far=(-2, 0)), grip=(25, 16), arrow=True, draw=5)),  # full draw
        F(A(hpose(lean=-1, near=(2, 0), far=(-2, 0)), grip=(25, 16), pull=(13, 15), fx="release")),  # release
        F(A(hpose(near=(2, 0), far=(-2, 0)), grip=(24, 17), pull=(14, 17))),
        F(A(hpose(near=(1, 0), far=(-1, 0)), grip=(23, 18))),
    ]
    hurt_p = hpose(lean=-1, hdx=-1, eyes="pain")
    hurt = [F(flash(A(hurt_p, grip=(22, 19), tilt=10))), F(A(hurt_p, grip=(22, 19), tilt=10))]
    death = [
        F(A(hpose(lean=-1, hdx=-1, hdy=-1, eyes="pain", far=(-2, 0)), grip=(21, 18), tilt=15)),
        F(A(hpose(kneel=True, eyes="pain"), grip=(22, 20), tilt=20)),
        F(A(hpose(kneel=True, ub=1, hdx=1, hdy=1, eyes="blink"), grip=(22, 23), tilt=50)),
        F(archer_lying(-1)),
        F(archer_lying(0)),
        F(archer_lying(1)),
    ]
    cast = [
        F(A(hpose(near=(1, 0), far=(-1, 0)), grip=(23, 13), tilt=-35, arrow=True, draw=1)),
        F(A(hpose(lean=-1, near=(2, 0), far=(-2, 0), cloth=1), grip=(24, 12), tilt=-45, arrow=True, draw=4)),
        F(A(hpose(lean=-1, near=(2, 0), far=(-2, 0), cloth=1), grip=(24, 12), tilt=-45, pull=(14, 12),
            fx="volley")),
        F(A(hpose(near=(1, 0), far=(-1, 0)), grip=(23, 14), tilt=-30, arrow=True, draw=2)),
    ]
    return build_sheet([idle, walk, attack, hurt, death, cast], 32, 32)


# ---------------------------------------------------------------- HUNTER
# brown hood with a pale fur rim, fur mantle, dark leather, khaki trousers, knives, bow on the back
HUNT3_HEAD = [
    "..bbb......",
    ".bcccbb....",
    "bccccbbba..",
    "bcccbbbbbaa",
    "bccbbzzzzza",
    "abbbz446665",
    "abbbz469695",
    "abbbz466665",
    ".aabyz4555.",
    "..aayyzzy..",
    "....yyy....",
]
HUNT3_LEATHER = "kab"
HUNT3_PANTS = "myz"
HUNT3_BOOT = "abc"
HUNT3_SPANS = [(-4, 4), (-5, 4), (-5, 4), (-5, 4), (-4, 4), (-4, 4), (-4, 4), (-4, 4), (-4, 4), (-4, 4)]


def hunter_v3(p: dict, nh=None, knife: float = 30, knife_shown: bool = True, fh=None,
              fx: str | None = None) -> Canvas:
    c = Canvas(32, 32)
    ub, lx = p["ub"], p["lean"]
    if p["kneel"]:
        ub += 3
    # bow slung across the back (arc behind the far shoulder)
    for i in range(16):
        x = CX - 6 + lx + round(i * 0.35 - 2.2 * math.sin(i / 15 * math.pi))
        c.set(x, 8 + ub + i, "c" if i < 7 else "b")
    c.line(CX - 6 + lx, 8 + ub, CX - 1 + lx, 23 + ub, "z")
    # short fur-trimmed cape behind
    fl = p["cloth"]
    for y in range(14 + ub, 25):
        k = y - 14 - ub
        x0 = round(CX - 6 + lx - k * 0.25 - (fl if k > 5 else 0))
        for x in range(x0, CX + lx):
            c.set(x, y, "y" if x == x0 else ("m" if x < x0 + 3 else "k"))
    legs_v3(c, p, HUNT3_PANTS, HUNT3_BOOT)
    block_v3(c, CX + lx, 13 + ub, HUNT3_SPANS, HUNT3_LEATHER, lit_rows=1)
    # crossed belts with spare knives, khaki sash
    for k in range(6):
        c.set(CX - 3 + lx + k, 15 + ub + k, "y" if k % 2 else "m")
    c.set(CX - 2 + lx, 18 + ub, "p")
    c.set(CX - 2 + lx, 19 + ub, "b")
    ring_v3(c, 20 + ub, CX - 4 + lx, CX + 4 + lx, "zyy", sag=1.0)
    c.set(CX + 1 + lx, 21 + ub, "q")
    # fur mantle over the shoulders: pale grey-beige tufts
    for y in range(11, 18):
        for x in range(CX - 7, CX + 8):
            nx, ny = (x + 0.5 - (CX + 0.2)) / 6.3, (y + 0.5 - 14.4) / 2.8
            if nx * nx + ny * ny <= 1:
                col = "W" if (ny < -0.3 and nx < -0.2) else ("z" if nx < 0.5 else "y")
                if ny > 0.5:
                    col = "y" if nx < 0.4 else "m"
                c.set(x + lx, y + ub, col)
    for x in range(CX - 5, CX + 6):
        if (x - CX) % 3 == 1:
            c.set(x + lx, 17 + ub, None if c.get(x + lx, 18 + ub) is None else "k")
        elif (x - CX) % 3 == 0:
            c.set(x + lx, 18 + ub, "y" if x < CX else "m")
    c.stamp(HUNT3_HEAD, 10 + lx + p["hdx"], 2 + ub + p["hdy"],
            remap={"4": "h", "5": "i", "6": "j", "9": "o" if p["eyes"] != "blink" else "h"})
    if p["eyes"] == "pain":
        for (x, y) in ((7, 6), (9, 6)):
            c.set(10 + lx + p["hdx"] + x, 2 + ub + p["hdy"] + y, "h")
            c.set(10 + lx + p["hdx"] + x, 1 + ub + p["hdy"] + y, "a")
    nhx, nhy = nh if nh else (20 - p["swing"] // 2, 21)
    nhx, nhy = nhx + lx, nhy + ub
    if fh:
        arm_v3(c, CX - 2 + lx, 15 + ub, fh[0] + lx, fh[1] + ub, "kab", cuff="y")
    if knife_shown:
        draw_knife(c, nhx, nhy, knife)
    arm_v3(c, CX + 3 + lx, 15 + ub, nhx, nhy, "kab", cuff="y")
    if fx == "throw":
        sparks(c, ((26, 13, "W"), (28, 13, "z"), (29, 14, "W"), (24, 12, "z")))
    if fx in ("call", "call2"):
        d = 1 if fx == "call2" else 0
        sparks(c, ((24, 8, "W"), (25, 9, "W"), (25, 10, "W"), (24, 11, "W"),
                   (27, 7, "z"), (28, 8, "z"), (28, 9, "z"), (28, 10, "z"), (27, 11, "z")), 0, d)
    if fx == "call2":
        sparks(c, ((30, 7, "y"), (30, 12, "y"), (31, 9, "y"), (27, 3, "s")))
    return c


def hunter_lying(stage: int) -> Canvas:
    c = Canvas(32, 32)
    draw_knife(c, 22, 19, 10)
    lying_v3(c, stage, "kab", "hij", HUNT3_LEATHER, HUNT3_PANTS, HUNT3_BOOT, collar="myz",
             hood="abcz")
    return c


def hunter_sheet_v3() -> Canvas:
    F = finish
    Hn = hunter_v3
    idle = [F(Hn(hpose(ub=b, cloth=(i in (1, 2)), eyes="blink" if i == 3 else "open"))) for i, b in
            enumerate((0, 0, 1, 1))]
    walk = [F(Hn(p, knife=30 + p["swing"] * 8)) for p in walk_poses()]
    attack = [
        F(Hn(hpose(lean=-1, near=(1, 0), far=(-1, 0)), nh=(10, 10), knife=-150)),             # wind-up
        F(Hn(hpose(lean=-1, ub=-1, near=(1, 0), far=(-2, 0)), nh=(12, 6), knife=-120)),
        F(Hn(hpose(lean=1, ub=1, near=(2, 0), far=(-2, 0)), nh=(24, 14), knife_shown=False, fx="throw")),
        F(Hn(hpose(lean=1, ub=1, near=(2, 0), far=(-2, 0)), nh=(22, 19), knife_shown=False)),
        F(Hn(hpose(near=(1, 0), far=(-1, 0)), nh=(20, 21), knife=30)),
    ]
    hurt_p = hpose(lean=-1, hdx=-1, eyes="pain")
    hurt = [F(flash(Hn(hurt_p, nh=(18, 20), knife=60))), F(Hn(hurt_p, nh=(18, 20), knife=60))]
    death = [
        F(Hn(hpose(lean=-1, hdx=-1, hdy=-1, eyes="pain", far=(-2, 0)), nh=(17, 19), knife=80)),
        F(Hn(hpose(kneel=True, eyes="pain"), nh=(20, 21), knife=60)),
        F(Hn(hpose(kneel=True, ub=1, hdx=1, hdy=1, eyes="blink"), nh=(21, 23), knife_shown=False)),
        F(hunter_lying(-1)),
        F(hunter_lying(0)),
        F(hunter_lying(1)),
    ]
    cast = [
        F(Hn(hpose(), nh=(20, 10), knife_shown=False)),                                       # hand to mouth
        F(Hn(hpose(), nh=(20, 10), knife_shown=False, fx="call")),
        F(Hn(hpose(ub=-1, near=(1, 0), far=(-1, 0)), nh=(23, 4), knife_shown=False, fx="call2")),
        F(Hn(hpose(near=(1, 0), far=(-1, 0)), nh=(22, 8), knife_shown=False)),
    ]
    return build_sheet([idle, walk, attack, hurt, death, cast], 32, 32)


# ======================================================================================
# COMPANION WOLF 24x24 (hunter's summon: warm brown fur, red bandana, tail up)
# ======================================================================================
COMPANION_FUR = {"m": "b", "n": "c", "p": "d", "z": "j", "D": "a"}


def wolf_companion(bob: int = 0, dx: int = 0, drop: int = 0, head_dy: int = 0, **kw) -> Canvas:
    c = wolf(bob=bob, dx=dx, drop=drop, head_dy=head_dy, **kw)
    c.recolor(COMPANION_FUR, keep="or")
    by = 13 + bob + drop
    # red bandana knotted around the neck, tip hanging down the chest
    for (x, y, col) in ((14, by - 1, "S"), (15, by, "S"), (16, by, "S"), (17, by + 1, "S"), (15, by + 1, "R"),
                        (16, by + 1, "S"), (16, by + 2, "R"), (13, by - 1, "R")):
        c.set(x + dx, y, col)
    # light muzzle/brow so it reads friendlier than the grey wolf
    c.set(14 + dx, by - 4 + head_dy, "g")
    return c


def sparkle_dissolve(body: Canvas, stage: int, seed: int = 3) -> Canvas:
    """Despawn: pixels drop out in a fixed random order, survivors on the edge turn to gold sparks."""
    rnd = random.Random(seed)
    pts = [(x, y) for y in range(body.h) for x in range(body.w) if body.px[y][x] not in (None, "o")]
    rnd.shuffle(pts)
    keep_frac = {1: 0.6, 2: 0.3, 3: 0.1, 4: 0.0}[stage]
    keep = set(pts[:int(len(pts) * keep_frac)])
    out = Canvas(body.w, body.h)
    for (x, y) in keep:
        out.px[y][x] = body.px[y][x]
    out.outline("o")
    # sparks drifting up from the removed pixels
    rnd2 = random.Random(seed + stage)
    lost = pts[int(len(pts) * keep_frac):]
    rnd2.shuffle(lost)
    for (x, y) in lost[:{1: 6, 2: 8, 3: 7, 4: 4}[stage]]:
        out.set(x, y - stage * 2, rnd2.choice("sWr"))
    return out


def wolf_companion_sheet() -> Canvas:
    F = finish
    W = wolf_companion
    idle = [F(W(bob=b, tail=t)) for b, t in ((0, 1), (0, 2), (1, 2), (1, 1))]
    pat = [(2, -1, -1, 2), (1, 0, 0, 1), (-1, 2, 2, -1), (-2, 1, 1, -2), (-1, 0, 0, -1), (1, -2, -2, 1)]
    lift = [(0, 1, 1, 0), (1, 0, 0, 1), (0, 1, 1, 0), (0, 0, 0, 0), (1, 0, 0, 1), (0, 0, 0, 0)]
    walk = [F(W(bob=(1 if i in (1, 4) else 0), legs=pat[i], lifts=lift[i], tail=1 + i % 2)) for i in range(6)]
    attack = [
        F(W(dx=-1, drop=1, head_dy=1, legs=(-1, -1, 1, 1), leg_len=6, tail=1)),
        F(W(dx=0, bob=-1, legs=(-2, -2, 2, 2), lifts=(1, 1, 0, 0), open_mouth=True, tail=2)),
        F(W(dx=1, bob=0, legs=(-2, -1, 2, 1), open_mouth=True, head_dy=1, tail=2)),
        F(W(dx=1, legs=(-1, -1, 1, 1), head_dy=1, tail=1)),
        F(W(dx=0, tail=1)),
    ]
    hurt = [F(flash(W(dx=-1, head_dy=-1))), F(W(dx=-1, head_dy=-1))]
    body = W(tail=1)
    death = [F(flash(W(tail=1)))] + [sparkle_dissolve(body, k) for k in (1, 2, 3, 4)] + [Canvas(24, 24)]
    return build_sheet([idle, walk, attack, hurt, death], 24, 24)


# ======================================================================================
# Hero projectiles 8x8 (point RIGHT) and skill VFX 64x64
# ======================================================================================
def arcane_bolt_sprite() -> Canvas:
    c = Canvas(8, 8)
    c.set(0, 4, "L")
    c.set(1, 4, "M")
    c.set(1, 3, "L")
    c.set(2, 5, "M")
    c.shaded_ellipse(4.6, 4, 2.6, 2.6, "MNC")
    c.set(4, 3, "W")
    c.set(5, 3, "C")
    c.set(4, 4, "C")
    c.outline("K")
    c.set(7, 1, "C")  # spark ahead of the orb
    c.set(1, 6, "N")
    return c


def holy_bolt_sprite() -> Canvas:
    c = Canvas(8, 8)
    c.set(0, 4, "r")
    c.set(1, 4, "s")
    c.set(1, 3, "r")
    c.shaded_ellipse(4.6, 4, 2.6, 2.6, "rsW")
    c.set(4, 4, "x")
    c.set(5, 4, "x")
    c.set(4, 3, "W")
    c.set(5, 5, "w")
    c.outline("q")
    c.set(7, 1, "W")
    return c


def knife_sprite() -> Canvas:
    c = Canvas(8, 8)
    c.set(0, 4, "r")
    c.set(1, 4, "b")
    c.set(2, 3, "q")
    c.set(2, 4, "r")
    c.set(2, 5, "q")
    c.line(3, 4, 5, 4, "p")
    c.line(3, 3, 5, 3, "z")
    c.set(6, 4, "W")
    c.set(6, 3, "p")
    c.outline("o")
    return c


def ring_vfx(ramp: str, inner: str, sparks: str, seed: int) -> Canvas:
    """64x64 burst ring like nova.png. ramp = outer..inner colours of the main band."""
    c = Canvas(64, 64)
    n = len(ramp)
    for y in range(64):
        for x in range(64):
            r = math.hypot(x + 0.5 - 32, y + 0.5 - 32)
            if 26.5 <= r <= 31.5:
                d = (31.5 - r) / 5.0
                c.set(x, y, ramp[min(n - 1, int(d * n))])
            elif 21.5 <= r <= 22.5 and (int(math.degrees(math.atan2(y - 32, x - 32)) + 360) // 20) % 2 == 0:
                c.set(x, y, inner)
    rnd = random.Random(seed)
    for k in range(10):
        a = math.radians(k * 36 + rnd.uniform(-8, 8))
        r0, r1 = rnd.uniform(9, 13), rnd.uniform(17, 21)
        for i in range(int(r1 - r0) + 1):
            rr = r0 + i
            col = sparks[0] if i > (r1 - r0) * 0.6 else sparks[1]
            c.set(32 + math.cos(a) * rr, 32 + math.sin(a) * rr, col)
    for k in range(8):
        a = math.radians(k * 45 + 22)
        c.set(32 + math.cos(a) * 25, 32 + math.sin(a) * 25, "W")
    return c


def arcane_blast_vfx() -> Canvas:
    return ring_vfx("LMNNC", "N", "WN", seed=13)


def heal_wave_vfx() -> Canvas:
    """Green-gold ring with floating healing crosses instead of arcane shards."""
    c = Canvas(64, 64)
    for y in range(64):
        for x in range(64):
            r = math.hypot(x + 0.5 - 32, y + 0.5 - 32)
            if 26.5 <= r <= 31.5:
                d = (31.5 - r) / 5.0
                c.set(x, y, "uvxsW"[min(4, int(d * 5))])
            elif 22.5 <= r <= 23.5 and (int(math.degrees(math.atan2(y - 32, x - 32)) + 360) // 15) % 3 == 0:
                c.set(x, y, "s")
    for k in range(8):
        a = math.radians(k * 45 + 22.5)
        rr = 16 if k % 2 else 19
        cx_, cy_ = round(32 + math.cos(a) * rr), round(32 + math.sin(a) * rr)
        for (dx, dy, col) in ((0, 0, "W"), (1, 0, "x"), (-1, 0, "x"), (0, 1, "w"), (0, -1, "x"),
                              (2, 0, "w"), (-2, 0, "x"), (0, 2, "w"), (0, -2, "x")):
            c.set(cx_ + dx, cy_ + dy, col)
    for k in range(8):
        a = math.radians(k * 45)
        c.set(32 + math.cos(a) * 10, 32 + math.sin(a) * 10, "s")
    return c


# ======================================================================================
# Projectiles, items, VFX
# ======================================================================================
def arrow_sprite() -> Canvas:
    c = Canvas(8, 8)
    c.line(1, 4, 5, 4, "c")
    c.set(2, 3, "d")
    c.set(6, 4, "p")
    c.set(7, 4, "W")
    c.set(6, 3, "p")
    c.set(6, 5, "n")
    c.set(0, 3, "S")
    c.set(1, 3, "S")
    c.set(0, 5, "R")
    c.set(1, 5, "R")
    return c


def bolt_sprite() -> Canvas:
    c = Canvas(8, 8)
    c.set(0, 4, "v")
    c.set(1, 3, "w")
    c.shaded_ellipse(4.5, 4, 2.6, 2.6, "vwx")
    c.set(4, 3, "W")
    c.set(5, 3, "s")
    c.outline("t")
    return c


def potion_icon() -> Canvas:
    c = Canvas(16, 16)
    c.shaded_ellipse(8, 10, 5.2, 4.8, "RSS")
    c.rect(6, 3, 4, 3, "C")
    c.rect(7, 3, 2, 3, "B")
    c.rect(6, 1, 4, 2, "c")
    c.set(6, 1, "d")
    c.rect(5, 5, 6, 1, "B")
    # glass highlight + liquid surface
    c.line(4, 8, 5, 7, "W")
    c.set(4, 9, "C")
    for x in range(4, 13):
        if c.get(x, 7) == "S":
            c.set(x, 7, "g")
    c.set(10, 12, "g")
    return finish(c)


def sword_icon() -> Canvas:
    c = Canvas(16, 16)
    draw_sword(c, 4, 11, -45, length=11)
    return finish(c)


def coin_icon() -> Canvas:
    c = Canvas(8, 8)
    c.shaded_ellipse(4, 4, 3.4, 3.4, "qrrs")
    c.line(4, 2, 4, 5, "q")
    c.set(3, 2, "s")
    c.set(2, 3, "s")
    c.outline("o")
    return c


def slash_vfx() -> Canvas:
    c = Canvas(32, 32)
    for y in range(32):
        for x in range(16, 32):
            dx, dy = x + 0.5 - 12, y + 0.5 - 16
            r = math.hypot(dx, dy)
            a = math.atan2(dy, dx)  # -pi/2..pi/2 on the right side
            if abs(a) > 1.35:
                continue
            k = 1 - abs(a) / 1.35  # 1 in the middle, 0 at the tips
            thick = 1.0 + 3.6 * k
            outer = 17.5
            if outer - thick <= r <= outer:
                depth = (outer - r) / thick
                c.set(x, y, "W" if depth < 0.45 else ("z" if depth < 0.8 else "p"))
    return c


def nova_vfx() -> Canvas:
    c = Canvas(64, 64)
    for y in range(64):
        for x in range(64):
            r = math.hypot(x + 0.5 - 32, y + 0.5 - 32)
            if 27.5 <= r <= 31.5:
                d = 31.5 - r
                c.set(x, y, "q" if d < 0.9 else ("r" if d < 2.1 else ("s" if d < 3.2 else "W")))
            elif 23.5 <= r <= 24.5 and (int(math.degrees(math.atan2(y - 32, x - 32))) // 15) % 2 == 0:
                c.set(x, y, "s")
    for ang in range(0, 360, 45):
        t = math.radians(ang + 22)
        sx, sy = 32 + math.cos(t) * 20, 32 + math.sin(t) * 20
        c.set(sx, sy, "W")
        c.set(sx + 1, sy, "s")
        c.set(sx - 1, sy, "s")
        c.set(sx, sy + 1, "s")
        c.set(sx, sy - 1, "s")
    return c


# ======================================================================================
# Ground textures (seamless 64x64)
# ======================================================================================
def periodic_noise(size: int, cells: int, seed: int) -> list[list[float]]:
    rnd = random.Random(seed)
    g = [[rnd.random() for _ in range(cells)] for _ in range(cells)]
    out = []
    step = size / cells
    for y in range(size):
        row = []
        for x in range(size):
            fx, fy = x / step, y / step
            x0, y0 = int(fx) % cells, int(fy) % cells
            x1, y1 = (x0 + 1) % cells, (y0 + 1) % cells
            tx, ty = fx - int(fx), fy - int(fy)
            tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
            a = g[y0][x0] * (1 - tx) + g[y0][x1] * tx
            b = g[y1][x0] * (1 - tx) + g[y1][x1] * tx
            row.append(a * (1 - ty) + b * ty)
        out.append(row)
    return out


def wrap_set(c: Canvas, x: int, y: int, col: str) -> None:
    c.px[y % c.h][x % c.w] = col


def calm_patches(S: int, seed: int, base: str, shade: str, amount: float = 0.38) -> Canvas:
    """Two close tones in big soft patches (low-frequency noise only: no specks, no dither)."""
    c = Canvas(S, S)
    n1 = periodic_noise(S, 2, seed)
    n2 = periodic_noise(S, 4, seed + 1)
    n3 = periodic_noise(S, 8, seed + 2)
    vals = [[n1[y][x] * 0.45 + n2[y][x] * 0.4 + n3[y][x] * 0.15 for x in range(S)] for y in range(S)]
    th = sorted(v for row in vals for v in row)[int(S * S * amount)]  # amount = shaded fraction
    for y in range(S):
        for x in range(S):
            c.px[y][x] = shade if vals[y][x] < th else base
    # remove 1-px islands and notches so patch edges stay clean
    for _ in range(2):
        src = [row[:] for row in c.px]
        for y in range(S):
            for x in range(S):
                nb = [src[(y + dy) % S][(x + dx) % S] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
                other = shade if src[y][x] == base else base
                if sum(1 for q in nb if q == other) >= 3:
                    c.px[y][x] = other
    return c


class Scatter:
    """Picks well-spaced points on a wrapping tile (deterministic)."""

    def __init__(self, S: int, seed: int, gap: int) -> None:
        self.S, self.rnd, self.gap, self.spots = S, random.Random(seed), gap, []

    def pick(self) -> tuple[int, int]:
        S = self.S
        for _ in range(400):
            x, y = self.rnd.randrange(S), self.rnd.randrange(S)
            if all(min(abs(x - a), S - abs(x - a)) + min(abs(y - b), S - abs(y - b)) > self.gap
                   for a, b in self.spots):
                self.spots.append((x, y))
                return x, y
        return self.rnd.randrange(S), self.rnd.randrange(S)


GRASS_TUFTS = (
    ["v.v", "Hv."],
    ["..v.", "v.v.", ".HH."],
    ["w..", "Hw.", ".H."],
)


def grass_tile() -> Canvas:
    """Warm sun-dried meadow: two close olive tones in big soft patches, a few tiny
    darker tufts and pebbles. Low contrast so characters and props pop."""
    S = 64
    c = calm_patches(S, 11, "G", "H", 0.30)
    sc = Scatter(S, 5, 13)
    for i in range(7):
        x, y = sc.pick()
        art = GRASS_TUFTS[i % len(GRASS_TUFTS)]
        for j, row in enumerate(art):
            for k, ch in enumerate(row):
                if ch != ".":
                    col = ch
                    if ch == "H" and c.px[(y + j) % S][(x + k) % S] == "H":
                        col = "E"  # tuft root on the darker patch stays a tone darker
                    wrap_set(c, x + k, y + j, col)
    # two tiny pebbles: lit top, darker underside (a tone darker, no outline)
    for _ in range(2):
        x, y = sc.pick()
        wrap_set(c, x, y, "y")
        wrap_set(c, x + 1, y, "F")
        wrap_set(c, x, y + 1, "F")
        wrap_set(c, x + 1, y + 1, "E")
    # one single pebble speck
    x, y = sc.pick()
    wrap_set(c, x, y, "F")
    wrap_set(c, x + 1, y, "E")
    return c


def cave_tile() -> Canvas:
    """Warm brown-grey stone floor: soft patches, faint slab joints a tone darker, pebbles."""
    S = 64
    c = calm_patches(S, 21, "P", "Q", 0.35)
    rnd = random.Random(9)
    seeds = [(rnd.uniform(0, S), rnd.uniform(0, S)) for _ in range(6)]
    for y in range(S):
        for x in range(S):
            ds = []
            for (sx, sy) in seeds:
                dx = min(abs(x + 0.5 - sx), S - abs(x + 0.5 - sx))
                dy = min(abs(y + 0.5 - sy), S - abs(y + 0.5 - sy))
                ds.append(math.sqrt(dx * dx + dy * dy))
            ds.sort()
            if ds[1] - ds[0] < 0.9:
                c.px[y][x] = "Q"
    sc = Scatter(S, 4, 14)
    # short cracks a tone darker than the shade
    for _ in range(2):
        x, y = sc.pick()
        for _ in range(4):
            wrap_set(c, x, y, "m")
            x += 1
            y += rnd.choice((0, 1))
    # pebbles: lit top + darker side
    for _ in range(4):
        x, y = sc.pick()
        wrap_set(c, x, y, "n")
        wrap_set(c, x + 1, y, "P")
        wrap_set(c, x, y + 1, "Q")
        wrap_set(c, x + 1, y + 1, "m")
    return c


def blob_mask(w: int, h: int, cx: float, cy: float, rx: float, ry: float, seed: int,
              wobble: float = 0.22, lobes: int = 5) -> list[list[float]]:
    """Signed 'depth' inside an irregular blob: >0 inside (1 at centre), <=0 outside."""
    rnd = random.Random(seed)
    harm = [(k, rnd.uniform(0, 2 * math.pi), rnd.uniform(0.3, 1.0)) for k in range(2, 2 + lobes)]
    norm = sum(a for _, _, a in harm)
    out = []
    for y in range(h):
        row = []
        for x in range(w):
            dx, dy = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
            ang = math.atan2(dy, dx)
            rr = 1 + wobble * sum(a * math.sin(k * ang + ph) for k, ph, a in harm) / norm
            row.append(1 - math.hypot(dx, dy) / rr)
        out.append(row)
    return out


def dirt_patch() -> Canvas:
    """48x32 trampled earth decal: irregular soft edge in a lighter tone, no outline."""
    w, h = 48, 32
    c = Canvas(w, h)
    m = blob_mask(w, h, 24, 16, 19.5, 12.0, seed=31, wobble=0.2)
    for y in range(h):
        for x in range(w):
            d = m[y][x]
            if d > 0.16:
                c.px[y][x] = "E"
            elif d > 0:
                c.px[y][x] = "F"
    # ragged rim: a few earth pixels poke out, a few rim pixels bite in
    rnd = random.Random(32)
    for y in range(h):
        for x in range(w):
            if c.px[y][x] == "F" and 0.06 < m[y][x] and rnd.random() < 0.18:
                c.px[y][x] = "E"
    # a few pebbles and footprints (tone lighter / darker, no outline)
    for (x, y) in ((14, 12), (31, 19)):
        c.set(x, y, "y")
        c.set(x + 1, y, "F")
        c.set(x, y + 1, "F")
    for (x, y) in ((20, 17), (26, 13)):
        c.rect(x, y, 3, 1, "F")
    return c


def grass_patch() -> Canvas:
    """32x24 clump of lush darker grass with a few flowers; blade-tip edge, no outline."""
    w, h = 32, 24
    c = Canvas(w, h)
    m = blob_mask(w, h, 16, 13.5, 13.0, 8.0, seed=41, wobble=0.18)
    for y in range(h):
        for x in range(w):
            d = m[y][x]
            if d > 0.38:
                c.px[y][x] = "u"
            elif d > 0:
                c.px[y][x] = "v"
    # blades sticking out of the top edge, lit tips
    rnd = random.Random(42)
    for x in range(3, w - 3):
        top = next((y for y in range(h) if c.px[y][x] is not None), None)
        if top is None or rnd.random() < 0.45:
            continue
        ln = rnd.choice((1, 2, 2, 3))
        for k in range(1, ln + 1):
            c.set(x, top - k, "v")
        c.set(x, top - ln, "w")
    # lit blade strokes inside (top-left light)
    for (x, y) in ((8, 8), (12, 6), (17, 7), (22, 9), (10, 12), (25, 13), (15, 11)):
        if c.get(x, y) and c.get(x, y + 1):
            c.set(x, y, "w")
            c.set(x, y + 1, "v")
    # dark blades low in the clump
    for (x, y) in ((11, 16), (19, 17), (23, 15), (14, 18)):
        if c.get(x, y) == "u":
            c.set(x, y, "t")
    # flowers: 3 small heads
    for (x, y, col, mid) in ((9, 9, "W", "r"), (21, 6, "s", "q"), (16, 14, "S", "g")):
        c.set(x, y - 1, col)
        c.set(x - 1, y, col)
        c.set(x + 1, y, col)
        c.set(x, y + 1, col)
        c.set(x, y, mid)
    return c


# ======================================================================================
# HUD icons 24x24 (light glyph, dark outline)
# ======================================================================================
def glyph_finish(c: Canvas) -> Canvas:
    c.outline("o")
    c.outline("o")  # 2px outline: reads on any button colour
    return c


def icon_attack() -> Canvas:
    c = Canvas(24, 24)
    for i in range(12):
        c.set(7 + i, 16 - i, "W")
        c.set(8 + i, 16 - i, "p")
    c.set(19, 5, "W")
    c.line(5, 13, 10, 18, "s")
    c.line(5, 14, 9, 18, "r")
    c.line(6, 17, 4, 19, "c")
    c.line(7, 17, 5, 19, "d")
    c.set(3, 20, "s")
    return glyph_finish(c)


def icon_skill() -> Canvas:
    c = Canvas(24, 24)
    pts = []
    for k in range(16):
        r = 9 if k % 2 == 0 else 4
        a = math.radians(k * 22.5 - 90)
        pts.append((12 + math.cos(a) * r, 12 + math.sin(a) * r))
    for y in range(24):
        for x in range(24):
            inside = False
            px_, py_ = x + 0.5, y + 0.5
            j = len(pts) - 1
            for i in range(len(pts)):
                xi, yi = pts[i]
                xj, yj = pts[j]
                if (yi > py_) != (yj > py_) and px_ < (xj - xi) * (py_ - yi) / (yj - yi) + xi:
                    inside = not inside
                j = i
            if inside:
                d = math.hypot(px_ - 12, py_ - 12)
                c.set(x, y, "W" if d < 3.5 else ("s" if d < 6 else "r"))
    return glyph_finish(c)


def icon_dash() -> Canvas:
    c = Canvas(24, 24)
    for ox, col in ((5, "p"), (11, "W")):
        for i in range(6):
            c.set(ox + i, 6 + i, col)
            c.set(ox + i + 1, 6 + i, col)
            c.set(ox + i, 17 - i, col)
            c.set(ox + i + 1, 17 - i, col)
    for (y, x0) in ((8, 1), (12, 0), (16, 1)):
        pass
    c.line(1, 9, 3, 9, "n")
    c.line(0, 14, 3, 14, "n")
    return glyph_finish(c)


def icon_bag() -> Canvas:
    c = Canvas(24, 24)
    c.shaded_ellipse(12, 14.5, 7.5, 6.5, "nzWW")
    c.rect(5, 13, 15, 1, "y")
    c.rect(10, 12, 4, 4, "r")
    c.set(11, 13, "s")
    c.rect(11, 14, 2, 1, "q")
    # handle/strap
    c.line(8, 9, 9, 5, "z")
    c.line(9, 5, 15, 5, "z")
    c.line(15, 5, 16, 9, "z")
    return glyph_finish(c)


def icon_use() -> Canvas:
    c = Canvas(24, 24)
    # open hand (palm facing viewer)
    c.rect(7, 11, 10, 8, "z")
    c.rect(8, 19, 8, 2, "z")
    for i, (x, top) in enumerate(((7, 6), (10, 4), (13, 4), (16, 6))):
        c.rect(x, top, 2, 11 - top + 1, "W")
    c.line(4, 12, 7, 15, "W")
    c.line(4, 11, 6, 13, "W")
    c.line(9, 16, 14, 16, "y")
    return glyph_finish(c)


def icon_pause() -> Canvas:
    c = Canvas(24, 24)
    c.rect(7, 5, 4, 14, "W")
    c.rect(13, 5, 4, 14, "W")
    c.rect(10, 5, 1, 14, "z")
    c.rect(16, 5, 1, 14, "z")
    return glyph_finish(c)


# ======================================================================================
# HUD stat icons 16x16 (top bar pills: gold, kills, timer, level) - coloured glyph with a
# light top-left, 1 px dark outline, like the resource icons of the style target
# ======================================================================================
def stat_gold() -> Canvas:
    c = Canvas(16, 16)
    c.ellipse(8, 8.5, 6.2, 6.2, "q")          # coin rim (shade)
    c.ellipse(7.6, 8.0, 5.6, 5.6, "r")
    c.ellipse(8.2, 8.6, 3.6, 3.6, "q")         # inner disc ring
    c.ellipse(7.9, 8.3, 3.0, 3.0, "r")
    c.line(8, 6, 8, 11, "q")                   # stamped mark, a tone darker
    c.line(7, 6, 7, 10, "s")
    for (x, y) in ((4, 5), (5, 4), (4, 6), (6, 3)):
        c.set(x, y, "s")
    c.set(4, 4, "W")
    return finish(c)


def stat_kills() -> Canvas:
    c = Canvas(16, 16)
    c.ellipse(8, 7, 5.6, 5.0, "z")             # cranium
    c.rect(5, 10, 6, 3, "z")                   # jaw
    c.rect(6, 13, 4, 1, "y")
    for x in (6, 8):                           # teeth gaps
        c.set(x, 12, "y")
        c.set(x, 13, None)
    c.rect(4, 7, 3, 3, "k")                    # eye sockets
    c.rect(9, 7, 3, 3, "k")
    c.set(4, 7, "y")
    c.set(11, 7, "y")
    c.set(8, 10, "k")                          # nose
    for y in range(3, 13):                     # right side a tone darker
        for x in range(11, 15):
            if c.get(x, y) == "z" and x + y * 0.2 > 12:
                c.set(x, y, "y")
    c.set(5, 3, "W")
    c.set(4, 4, "W")
    return finish(c)


def stat_timer() -> Canvas:
    c = Canvas(16, 16)
    # glass bulbs
    for y in range(3, 13):
        t = abs(y - 7.5)
        hw = 0.6 + max(0.0, t - 0.6) * 0.95
        for x in range(round(8 - hw - 0.5), round(8 + hw - 0.5) + 1):
            c.set(x, y, "C")
    c.set(5, 4, "W")
    c.set(5, 5, "W")
    # sand: bottom pile + falling stream + leftover on top
    for (x0, x1, y) in ((6, 9, 12), (6, 9, 11), (7, 8, 10), (7, 8, 5), (6, 9, 4)):
        c.line(x0, y, x1, y, "r")
    c.set(9, 12, "q")
    c.set(9, 4, "q")
    c.line(8, 6, 8, 9, "s")
    # wooden caps
    c.rect(3, 1, 10, 2, "b")
    c.rect(3, 1, 10, 1, "c")
    c.rect(3, 13, 10, 2, "b")
    c.rect(3, 13, 10, 1, "c")
    c.set(12, 2, "a")
    c.set(12, 14, "a")
    return finish(c)


def stat_level() -> Canvas:
    c = Canvas(16, 16)
    pts = []
    for k in range(10):
        r = 7.2 if k % 2 == 0 else 3.0
        a = math.radians(k * 36 - 90)
        pts.append((8 + math.cos(a) * r, 8.4 + math.sin(a) * r))
    for y in range(16):
        for x in range(16):
            px_, py_ = x + 0.5, y + 0.5
            inside = False
            j = len(pts) - 1
            for i in range(len(pts)):
                xi, yi = pts[i]
                xj, yj = pts[j]
                if (yi > py_) != (yj > py_) and px_ < (xj - xi) * (py_ - yi) / (yj - yi) + xi:
                    inside = not inside
                j = i
            if inside:
                # flat: lit upper-left half, shade lower-right
                c.set(x, y, "s" if (x - 8) + (y - 8) < -1 else ("r" if (x - 8) + (y - 8) < 4 else "q"))
    c.set(7, 4, "W")
    return finish(c)


# ======================================================================================
# Decor (forest)
# ======================================================================================
def fir_tree() -> Canvas:
    """32x48 fir, 3/4 view: stacked chunky cones with flat lit/mid/shade bands, a darker
    band under each tier, scalloped lower edges, short trunk. Base on the bottom row."""
    c = Canvas(32, 48)
    cx = 16
    # trunk + root flare (bottom row 46, outline goes to 47)
    c.rect(14, 39, 4, 8, "b")
    c.rect(14, 39, 1, 8, "c")
    c.rect(17, 39, 1, 8, "a")
    c.rect(12, 46, 8, 1, "b")
    c.set(12, 46, "c")
    c.set(19, 46, "a")
    c.set(13, 45, "b")
    c.set(18, 45, "a")
    tiers = [(41, 14.5, 25), (32, 11.5, 17), (23, 8.5, 9), (14, 5.5, 2)]  # (base, half width, top)
    for ti, (base, half, top) in enumerate(tiers):
        tier = Canvas(32, 48)
        for y in range(top, base + 1):
            t = (y - top) / max(1, base - top)
            hw = 0.8 + (half - 0.8) * t ** 0.85
            for x in range(round(cx - hw), round(cx + hw) + 1):
                u = (x + 0.5 - (cx - hw)) / (2 * hw)
                col = "w" if u < 0.17 else ("v" if u < 0.5 else ("u" if u < 0.82 else "t"))
                if y == base:  # underside of the tier, a tone darker
                    col = "u" if u < 0.5 else "t"
                tier.set(x, y, col)
        # drooping branch tips: 2-px bumps under the tier edge
        x0, x1 = round(cx - half), round(cx + half)
        for x in range(x0 + 1, x1, 4):
            for k in (0, 1):
                if tier.get(x + k, base) is not None:
                    tier.set(x + k, base + 1, "u" if x + k < cx else "t")
        # one lit branch stroke per tier (top-left light)
        lx, ly = round(cx - half * 0.45), round(base - (base - top) * 0.35)
        tier.set(lx, ly, "w")
        tier.set(lx + 1, ly - 1, "w")
        c.blit(tier, 0, 0)
    c.set(cx - 1, 3, "w")
    return finish(c.shifted(0, -1))


def bush() -> Canvas:
    """16x16 round leafy bush, three flat-shaded clumps and a few red berries."""
    c = Canvas(16, 16)
    for (x, y, r) in ((8.0, 7.0, 4.6), (4.8, 10.2, 3.9), (11.2, 10.2, 3.9)):
        clump(c, x, y, r, r * 0.88, "v", "u", "t", rim=1.4)
    # flat bottom on row 13 (outline lands on 14, 1 px margin below)
    for x in range(16):
        if c.get(x, 14) is not None:
            c.set(x, 14, None)
        if c.get(x, 13) is not None:
            c.set(x, 13, "t")
    # leaf notches a tone darker, lit leaf tips
    for (x, y) in ((6, 9), (10, 6), (9, 11), (12, 9)):
        if c.get(x, y) is not None:
            c.set(x, y, DARKER[c.get(x, y)])
    for (x, y) in ((5, 5), (2, 9), (7, 4), (6, 4), (11, 7)):
        if c.get(x, y) is not None:
            c.set(x, y, "w")
    for (x, y) in ((5, 10), (11, 8), (12, 11)):
        c.set(x, y, "S")
        c.set(x, y - 1, "g")
    return finish(c)


def rock() -> Canvas:
    """16x16 chunky boulder in 3/4: lit top face, mid front, dark right side; small moss cap."""
    c = Canvas(16, 16)
    c.ellipse(7.6, 9.6, 6.6, 4.6, "n")       # body
    c.ellipse(12.2, 11.4, 3.0, 2.6, "n")      # small side stone
    # dark right/bottom side
    for y in range(16):
        for x in range(16):
            if c.get(x, y) == "n":
                lx = (x + 0.5 - 7.6) / 6.6
                ly = (y + 0.5 - 9.6) / 4.6
                if lx * 0.8 + ly * 0.9 > 0.55 or (x >= 11 and y >= 11 and (x - 12.2) + (y - 11.4) > 0.8):
                    c.set(x, y, "m")
    # top face (flat light plane)
    c.ellipse(6.6, 7.4, 4.6, 2.3, "p")
    c.set(4, 6, "W")
    c.set(5, 6, "W")
    # crack a tone darker
    c.set(9, 10, "m")
    c.set(10, 11, "m")
    c.set(8, 9, "m")
    # flat bottom
    for x in range(16):
        c.set(x, 14, None)
    # moss on the top-left
    for (x, y, col) in ((3, 7, "v"), (4, 7, "w"), (3, 8, "v"), (5, 7, "v"), (2, 9, "u")):
        if c.get(x, y) is not None:
            c.set(x, y, col)
    return finish(c)


def stump() -> Canvas:
    """16x16 tree stump: cut top with a ring, bark front lit left, roots."""
    c = Canvas(16, 16)
    c.rect(3, 7, 10, 7, "b")
    c.rect(3, 7, 2, 7, "c")
    c.rect(11, 7, 2, 7, "a")
    # roots
    c.rect(1, 12, 3, 2, "b")
    c.set(1, 12, "c")
    c.rect(12, 12, 3, 2, "a")
    c.rect(6, 13, 2, 1, "a")
    # bark grooves a tone darker
    for (x, y0, y1) in ((6, 9, 12), (9, 8, 11)):
        c.line(x, y0, x, y1, "a")
    c.line(4, 9, 4, 11, "b")
    # cut top face
    c.ellipse(8, 7, 5.2, 2.4, "d")
    c.ellipse(8, 7, 3.2, 1.4, "c")
    c.set(8, 7, "d")
    c.set(7, 7, "d")
    c.set(5, 6, "j")
    return finish(c)


def log() -> Canvas:
    """32x16 fallen log lying left-right: lit top strip, cut end with rings, moss patch."""
    c = Canvas(32, 16)
    for x in range(3, 27):
        c.set(x, 6, "c")
        c.set(x, 7, "c")
        for y in range(8, 11):
            c.set(x, y, "b")
        c.set(x, 11, "a")
        c.set(x, 12, "a")
    # broken left end: jagged
    for (x, y) in ((3, 6), (3, 7), (4, 6), (3, 12), (2, 9), (2, 10), (2, 8)):
        c.set(x, y, None if y in (6, 7, 12) and x == 3 else "b")
    c.set(2, 8, "c")
    c.set(4, 6, None)
    # bark grooves (a tone darker)
    for (x0, x1, y) in ((6, 11, 9), (14, 20, 10), (21, 25, 8), (9, 13, 11)):
        c.line(x0, y, x1, y, "a" if y > 8 else "b")
    # cut end (facing the viewer-right): ring face
    c.ellipse(27.2, 9.0, 2.9, 3.6, "d")
    c.ellipse(27.4, 9.0, 1.7, 2.3, "c")
    c.set(27, 9, "d")
    c.set(26, 6, "j")
    # moss on top + a little sprout
    for (x, y, col) in ((10, 6, "v"), (11, 6, "w"), (12, 6, "v"), (11, 7, "v"), (12, 7, "u"), (13, 6, "u"),
                        (18, 6, "w"), (19, 6, "v"), (18, 7, "v")):
        c.set(x, y, col)
    c.set(15, 5, "v")
    c.set(15, 4, "w")
    c.set(16, 5, "v")
    return finish(c.shifted(0, 1))


def flowers() -> Canvas:
    """16x16 small flower clump (ground decal): three heads on short stems with leaves."""
    c = Canvas(16, 16)
    # leaves + stems
    for (x, y, col) in ((4, 12, "v"), (5, 13, "u"), (6, 12, "w"), (9, 12, "v"), (10, 13, "u"), (11, 12, "w"),
                        (7, 13, "v"), (8, 13, "u"), (3, 13, "u"), (12, 13, "u")):
        c.set(x, y, col)
    c.line(5, 8, 5, 12, "u")
    c.line(10, 6, 10, 12, "u")
    c.line(8, 10, 8, 12, "v")
    # heads: plus-shaped petals, gold centre
    for (x, y, pet, sh, mid) in ((5, 7, "W", "z", "r"), (10, 5, "s", "r", "q"), (8, 9, "S", "e", "g")):
        c.set(x, y - 1, pet)
        c.set(x - 1, y, pet)
        c.set(x + 1, y, sh)
        c.set(x, y + 1, sh)
        c.set(x, y, mid)
    return finish(c)


def mushroom() -> Canvas:
    """16x16 two mushrooms: big red cap with pale dots, small brown one behind."""
    c = Canvas(16, 16)
    # small brown mushroom (behind, right)
    c.rect(11, 10, 2, 4, "z")
    c.set(12, 10, "y")
    c.set(12, 11, "y")
    c.ellipse(11.8, 9.4, 2.6, 1.7, "c")
    c.set(11, 8, "d")
    c.set(13, 10, "b")
    c.set(14, 9, "b")
    # big red mushroom
    c.rect(5, 9, 4, 5, "z")
    c.rect(8, 9, 1, 5, "y")
    c.set(5, 13, "y")
    c.ellipse(6.8, 7.6, 5.0, 3.2, "S")
    for y in range(16):
        for x in range(16):
            if c.get(x, y) == "S" and ((x - 6.8) * 0.6 + (y - 7.6) * 1.0 > 1.2):
                c.set(x, y, "e")
    for x in range(3, 11):  # cap rim underside
        if c.get(x, 9) in ("S", "e"):
            c.set(x, 9, "e")
    for (x, y) in ((4, 7), (7, 6), (9, 8)):
        c.set(x, y, "W")
    c.set(5, 5, "g")
    c.set(6, 5, "g")
    # grass at the base
    for (x, y, col) in ((3, 13, "v"), (4, 13, "u"), (9, 13, "u"), (10, 13, "v"), (14, 13, "v")):
        c.set(x, y, col)
    return finish(c)


def ruin_pillar() -> Canvas:
    """16x32 broken stone pillar: block joints a tone darker, jagged broken top showing its
    top face, wider plinth, moss on the top and base."""
    c = Canvas(16, 32)
    # plinth
    c.rect(2, 26, 12, 4, "n")
    c.rect(2, 26, 12, 1, "p")
    c.rect(2, 27, 2, 3, "p")
    c.rect(12, 27, 2, 3, "m")
    # shaft
    for y in range(9, 26):
        for x in range(4, 12):
            c.set(x, y, "p" if x < 6 else ("n" if x < 10 else "m"))
    # flutes (a tone darker)
    for x in (7, 9):
        c.line(x, 11, x, 25, DARKER["n"] if x == 9 else "n")
    c.line(6, 11, 6, 25, "n")
    # block joints
    for y in (15, 21):
        for x in range(4, 12):
            c.set(x, y, DARKER[c.get(x, y)])
    # broken top: jagged profile, top face visible (light)
    prof = {4: 9, 5: 7, 6: 6, 7: 7, 8: 8, 9: 6, 10: 5, 11: 7}
    for x, top in prof.items():
        for y in range(top, 9):
            c.set(x, y, "p" if x < 6 else ("n" if x < 10 else "m"))
        c.set(x, top, "W" if x < 8 else "p")
    c.set(10, 5, "p")
    # chip missing on the right edge
    c.set(11, 17, None)
    c.set(11, 18, None)
    c.set(10, 18, "m")
    # moss
    for (x, y, col) in ((5, 7, "w"), (6, 6, "w"), (7, 7, "v"), (4, 9, "v"), (4, 10, "u"), (5, 8, "v"),
                        (2, 25, "v"), (3, 25, "w"), (4, 25, "v"), (3, 24, "v"), (2, 29, "u"), (3, 29, "v"),
                        (12, 25, "u"), (13, 25, "v"), (11, 24, "u"), (8, 16, "v"), (7, 16, "u")):
        c.set(x, y, col)
    for y in range(30, 32):
        for x in range(16):
            c.set(x, y, None)
    return finish(c)


# ======================================================================================
# Decor (cave) - style v2, 3/4 view, base (bottom outline row) on h-2, no baked shadows
# ======================================================================================
def stone(c: Canvas, cx: float, cy: float, rx: float, ry: float, ramp: str = "mnp", top: float = 0.45) -> None:
    """Small 3/4 stone: dark lower-right side, mid front, light top face (upper-left)."""
    for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
        for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
            nx, ny = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
            if nx * nx + ny * ny > 1:
                continue
            if ny < -top + 0.25 * nx and nx < 0.6:
                col = ramp[2]
            elif nx * 0.7 + ny * 0.8 > 0.45:
                col = ramp[0]
            else:
                col = ramp[1]
            c.set(x, y, col)


BONES = [
    "................",
    "................",
    "................",
    "......zzzz......",
    ".....zWWzzz.....",
    "....zWzzzzzy....",
    "....zzzzzzzy....",
    "....zkkzkkzy..zz",
    "....zkkzkkyy.zzy",
    "....yzzkzzyy.zy.",
    ".zz..yzzzyy.zy..",
    "zWzz.zyzyzy.y...",
    "zyzzzzzzzzyzzz..",
    ".y..yyyyyyyyzWzy",
]


def bones() -> Canvas:
    """16x16 skull (3/4: cranium top lit, dark sockets) on two long bones."""
    c = Canvas(16, 16)
    c.stamp(BONES, 0, 0)
    return finish(c)


def crystal() -> Canvas:
    """16x24 glowing crystal cluster: three violet/blue prisms on a stone base, lit left facets."""
    c = Canvas(16, 24)

    def prism(x0: int, w: int, top: int, bottom: int, lean: int, ramp: str) -> None:
        # ramp = dark, mid, light, glow; pointed tip, left facet lit, right facet dark
        h = bottom - top
        for y in range(top, bottom + 1):
            t = (y - top) / max(1, h)
            sx = round(lean * (1 - t))
            if y - top < 2:  # tip
                ww = 1 if y == top else max(1, w - 2)
                xs = x0 + sx + (w - ww) // 2
                for x in range(xs, xs + ww):
                    c.set(x, y, ramp[3] if x == xs else ramp[2])
                continue
            for i in range(w):
                u = i / max(1, w - 1)
                col = ramp[2] if u < 0.34 else (ramp[1] if u < 0.67 else ramp[0])
                c.set(x0 + sx + i, y, col)
            c.set(x0 + sx, y, ramp[2])
        # glints
        c.set(x0 + round(lean * 0.6), top + 3, ramp[3])
        c.set(x0 + round(lean * 0.5), top + 4, ramp[3])

    prism(1, 4, 10, 20, -1, "KLMN")      # small violet, leaning left
    prism(10, 4, 8, 20, 2, "ABCW")       # blue, leaning right
    prism(5, 5, 2, 20, 0, "LMNW")        # tall violet centre
    # stone base
    stone(c, 5.5, 20.4, 5.0, 1.9)
    stone(c, 11.5, 20.6, 3.6, 1.6)
    for x in range(16):
        for y in (22, 23):
            c.set(x, y, None)
    # floating glow sparks (opaque palette pixels, no alpha)
    c = finish(c)
    for (x, y, col) in ((1, 5, "N"), (14, 4, "C"), (13, 1, "W")):
        c.set(x, y, col)
    return c


def stalagmite() -> Canvas:
    """16x32 stalagmite: tapered stone cone, lit left, drip rings a tone darker, wide base."""
    c = Canvas(16, 32)
    top, bottom = 3, 29
    for y in range(top, bottom + 1):
        t = (y - top) / (bottom - top)
        hw = 0.6 + 5.6 * t ** 1.25
        cx = 7.6 + 0.8 * math.sin(t * 2.4)
        x0, x1 = round(cx - hw), round(cx + hw)
        for x in range(x0, x1 + 1):
            u = (x - x0) / max(1, x1 - x0)
            col = "p" if u < 0.3 else ("n" if u < 0.72 else "m")
            c.set(x, y, col)
    # drip rings (a tone darker, curving down in the middle: 3/4)
    for yr in (10, 16, 22):
        row = [x for x in range(16) if c.get(x, yr) is not None]
        if not row:
            continue
        a, b = row[0], row[-1]
        for x in range(a, b + 1):
            u = (x - a) / max(1, b - a)
            y = yr + round(math.sin(math.pi * u))
            if c.get(x, y) is not None:
                if c.get(x, y) != "m":
                    c.set(x, y, DARKER[c.get(x, y)])
    c.set(7, 3, "W")
    c.set(7, 5, "p")
    # base stones
    stone(c, 3.0, 28.4, 2.6, 1.8)
    stone(c, 13.0, 28.6, 2.4, 1.6)
    for x in range(16):
        for y in (30, 31):
            c.set(x, y, None)
    return finish(c)


def cave_rubble() -> Canvas:
    """16x16 small stones scattered in a loose pile (warm grey, lit tops)."""
    c = Canvas(16, 16)
    for (x, y, rx, ry) in ((5.0, 10.6, 3.4, 2.6), (10.6, 11.8, 2.6, 1.9), (8.4, 8.0, 2.2, 1.8),
                           (2.4, 12.6, 1.6, 1.2), (13.4, 9.2, 1.5, 1.2)):
        stone(c, x, y, rx, ry)
    for (x, y) in ((4, 9), (9, 7)):
        c.set(x, y, "W")
    for x in range(16):
        c.set(x, 14, None)
        c.set(x, 15, None)
    return finish(c)


def cave_dirt_patch() -> Canvas:
    """48x32 cave ground decal: darker trampled earth, soft ragged edge, no outline."""
    w, h = 48, 32
    c = Canvas(w, h)
    m = blob_mask(w, h, 24, 16, 19.5, 12.0, seed=41, wobble=0.24)
    for y in range(h):
        for x in range(w):
            d = m[y][x]
            if d > 0.2:
                c.px[y][x] = "m"
            elif d > 0:
                c.px[y][x] = "Q"
    rnd = random.Random(42)
    for y in range(h):
        for x in range(w):
            if c.px[y][x] == "Q" and 0.1 < m[y][x] and rnd.random() < 0.15:
                c.px[y][x] = "m"
    # pebbles and scuffs (a tone lighter / darker, no outline)
    for (x, y) in ((15, 12), (32, 19), (25, 9)):
        c.set(x, y, "n")
        c.set(x + 1, y, "Q")
        c.set(x, y + 1, "m")
    for (x, y) in ((20, 18), (27, 14)):
        c.rect(x, y, 3, 1, "Q")
    return c


# ======================================================================================
# Previews (scratch only, --preview DIR)
# ======================================================================================
Pixel = tuple[int, int, int, int]
BLACK: Pixel = (0, 0, 0, 255)
SHADOW_RGB = RGBA["o"][:3]  # GroundShadow.COLOR, alpha 0.32 (drawn by code in game)


def upscale(rows: list[list[Pixel]], k: int) -> list[list[Pixel]]:
    out = []
    for row in rows:
        r = [p for p in row for _ in range(k)]
        for _ in range(k):
            out.append(list(r))
    return out


def compose(c: Canvas, bg: Canvas | None, solid: Pixel | None) -> list[list[Pixel]]:
    rows = []
    for y in range(c.h):
        row = []
        for x in range(c.w):
            p = c.px[y][x]
            if p is not None:
                row.append(RGBA[p])
            elif bg is not None:
                row.append(RGBA[bg.px[y % bg.h][x % bg.w]])
            else:
                row.append(solid)
        rows.append(row)
    return rows


def hstack(*panels: list[list[Pixel]], gap: int = 6) -> list[list[Pixel]]:
    h = max(len(p) for p in panels)
    out = []
    for y in range(h):
        row: list[Pixel] = []
        for i, p in enumerate(panels):
            w = len(p[0])
            row += p[y] if y < len(p) else [BLACK] * w
            if i < len(panels) - 1:
                row += [BLACK] * gap
        out.append(row)
    return out


def vstack(*panels: list[list[Pixel]], gap: int = 6) -> list[list[Pixel]]:
    w = max(len(p[0]) for p in panels)
    out = []
    for i, p in enumerate(panels):
        out += [r + [BLACK] * (w - len(r)) for r in p]
        if i < len(panels) - 1:
            out += [[BLACK] * w for _ in range(gap)]
    return out


def preview_pair(c: Canvas, ground: Canvas, k: int, path: Path, fw: int = 0, fh: int = 0) -> None:
    dark = (36, 28, 24, 255)
    a = upscale(compose(c, ground, None), k)
    b = upscale(compose(c, None, dark), k)
    if fw and fh:
        for y in range(len(b)):
            for x in range(len(b[0])):
                if (x % (fw * k) == 0 or y % (fh * k) == 0) and b[y][x] == dark:
                    b[y][x] = (58, 46, 40, 255)
    write_png(vstack(a, b, gap=4), path)


def sheet_frame(sheet: Canvas, fw: int, fh: int, row: int, col: int) -> Canvas:
    f = Canvas(fw, fh)
    for y in range(fh):
        for x in range(fw):
            f.px[y][x] = sheet.px[row * fh + y][col * fw + x]
    return f


class Scene:
    """RGBA scene: tiled ground, flat decals, then y-sorted objects with code-like shadows."""

    def __init__(self, w: int, h: int, ground: Canvas) -> None:
        self.w, self.h = w, h
        self.px = [[RGBA[ground.px[y % ground.h][x % ground.w]] for x in range(w)] for y in range(h)]
        self.objects: list[tuple[int, int, Canvas, float]] = []  # (base_y, x, sprite, shadow width)

    def decal(self, c: Canvas, cx: int, cy: int, mirror: bool = False) -> None:
        c = c.mirrored() if mirror else c
        self._blit(c, cx - c.w // 2, cy - c.h // 2)

    def obj(self, c: Canvas, x: int, base_y: int, shadow_w: float, mirror: bool = False) -> None:
        """x = centre, base_y = ground line (sprite's lowest outline row is at h-2)."""
        self.objects.append((base_y, x, c.mirrored() if mirror else c, shadow_w))

    def _blit(self, c: Canvas, ox: int, oy: int) -> None:
        for y in range(c.h):
            for x in range(c.w):
                p = c.px[y][x]
                if p is not None and 0 <= ox + x < self.w and 0 <= oy + y < self.h:
                    self.px[oy + y][ox + x] = RGBA[p]

    def _shadow(self, cx: float, cy: float, width: float) -> None:
        rx, ry = width / 2, width * 3 / 16
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                if 0 <= x < self.w and 0 <= y < self.h and \
                        ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1:
                    r, g, b, _ = self.px[y][x]
                    a = 0.32
                    self.px[y][x] = (round(r * (1 - a) + SHADOW_RGB[0] * a), round(g * (1 - a) + SHADOW_RGB[1] * a),
                                     round(b * (1 - a) + SHADOW_RGB[2] * a), 255)

    def render(self) -> list[list[Pixel]]:
        for base_y, x, c, sw in sorted(self.objects, key=lambda o: o[0]):
            if sw:
                self._shadow(x, base_y + 0.5, sw)
            self._blit(c, x - c.w // 2, base_y - (c.h - 2))
        self.objects = []
        return self.px


def read_png_rgba(path: Path) -> list[list[Pixel]]:
    """Minimal PNG reader (8-bit RGB/RGBA, non-interlaced) for the style target in previews."""
    data = path.read_bytes()
    pos, idat = 8, b""
    while pos < len(data):
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        tag, body = data[pos + 4:pos + 8], data[pos + 8:pos + 8 + ln]
        pos += 12 + ln
        if tag == b"IHDR":
            w, h, _, ct = struct.unpack(">IIBB", body[:10])
        elif tag == b"IDAT":
            idat += body
    bpp = 4 if ct == 6 else 3
    raw = zlib.decompress(idat)
    stride, prev, out, i = w * bpp, bytearray(w * bpp), [], 0
    for _ in range(h):
        f = raw[i]
        line = bytearray(raw[i + 1:i + 1 + stride])
        i += 1 + stride
        for x in range(stride):
            a = line[x - bpp] if x >= bpp else 0
            b = prev[x]
            cc = prev[x - bpp] if x >= bpp else 0
            if f == 1:
                line[x] = (line[x] + a) & 255
            elif f == 2:
                line[x] = (line[x] + b) & 255
            elif f == 3:
                line[x] = (line[x] + (a + b) // 2) & 255
            elif f == 4:
                pp = a + b - cc
                pa, pb, pc = abs(pp - a), abs(pp - b), abs(pp - cc)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else (b if pb <= pc else cc))) & 255
        prev = line
        out.append([tuple(line[x * bpp:x * bpp + 3]) + (255,) for x in range(w)])
    return out


def sample(img: list[list[Pixel]], w: int, h: int) -> list[list[Pixel]]:
    """Nearest-neighbour resample (preview comparison only, never for game sprites)."""
    H, W = len(img), len(img[0])
    return [[img[min(H - 1, int((y + 0.5) * H / h))][min(W - 1, int((x + 0.5) * W / w))] for x in range(w)]
            for y in range(h)]


def crop(img: list[list[Pixel]], x: int, y: int, w: int, h: int) -> list[list[Pixel]]:
    return [row[x:x + w] for row in img[y:y + h]]


def meadow_scene(ground: Canvas, sh: dict[str, Canvas], decor: dict[str, Canvas], cave: bool = False) -> list[list[Pixel]]:
    """360x640 phone screen at 1x: decals, props, 5 heroes, companion, enemies, boss."""
    W, H = 360, 640
    sc = Scene(W, H, ground)
    rnd = random.Random(77 if not cave else 78)
    if not cave:
        ground_decals = [("dirt_patch", 7), ("grass_patch", 9), ("flowers", 8), ("mushroom", 3)]
        props = [("fir_tree", 7), ("bush", 6), ("rock", 4), ("stump", 3), ("log", 2)]
    else:
        ground_decals = [("cave_dirt_patch", 7), ("mushroom", 3), ("cave_rubble", 6)]
        props = [("rock", 5), ("ruin_pillar", 2), ("stalagmite", 6), ("crystal", 5), ("bones", 5)]
    hero_zone = (60, 220, 300, 470)  # keep the middle readable

    def spot(margin: int = 10) -> tuple[int, int]:
        for _ in range(100):
            x, y = rnd.randrange(margin, W - margin), rnd.randrange(margin + 20, H - margin)
            if not (hero_zone[0] < x < hero_zone[2] and hero_zone[1] < y < hero_zone[3]):
                return x, y
        return x, y

    for name, n in ground_decals:
        for _ in range(n):
            x, y = spot()
            sc.decal(decor[name], x, y, rnd.random() < 0.5)
    for name, n in props:
        for _ in range(n):
            x, y = spot(14)
            sc.obj(decor[name], x, y, decor[name].w * 0.8, rnd.random() < 0.5)

    def f(k: str, size: int, row: int, col: int) -> Canvas:
        return sheet_frame(sh[k], size, size, row, col)

    heroes = ("warrior", "mage", "healer", "archer", "hunter")
    for i, k in enumerate(heroes):
        sc.obj(f(k, 32, 0, 0), 84 + i * 48, 300, 16)
        sc.obj(f(k, 32, 1, 2), 84 + i * 48, 360, 16, mirror=(i % 2 == 1))
    sc.obj(f("wolf_companion", 24, 1, 1), 300, 400, 12)
    for (k, x, y, row, col, mir) in (("goblin", 110, 420, 1, 2, True), ("goblin", 70, 250, 0, 0, False),
                                      ("wolf", 200, 430, 1, 1, True), ("wolf", 250, 250, 0, 1, True),
                                      ("skeleton", 160, 450, 0, 0, True), ("slime", 240, 450, 0, 1, False),
                                      ("goblin", 40, 520, 1, 4, False), ("skeleton", 330, 560, 2, 1, True)):
        sc.obj(f(k, 24, row, col), x, y, 14, mir)
    sc.obj(f("boss", 64, 0, 0), 260, 190, 44, mirror=True)
    return sc.render()


def write_previews(out: Path, sheets: dict[str, Canvas], singles: dict[str, Canvas], icons: dict[str, Canvas],
                   stat_icons: dict[str, Canvas], decor: dict[str, Canvas]) -> None:
    grass, cave = singles["grass"], singles["cave"]
    for name, sh in sheets.items():
        fw = 64 if name == "boss" else (32 if sh.w == 32 * 6 else 24)
        preview_pair(sh, grass, 4 if fw < 64 else 3, out / f"sheet_{name}.png", fw, fw)
    # in-game 1x screens + comparison with the style target
    meadow = meadow_scene(grass, sheets, decor)
    cavern = meadow_scene(cave, sheets, decor, cave=True)
    target_path = REPO / "docs" / "art" / "reference" / "style_target_base.png"
    target = sample(read_png_rgba(target_path), 360, 640) if target_path.exists() else [[BLACK] * 360] * 640
    write_png(hstack(target, meadow, cavern), out / "compare_target_1x.png")
    t3 = upscale(crop(sample(read_png_rgba(target_path), 360, 640), 150, 300, 120, 160), 3) \
        if target_path.exists() else [[BLACK] * 360] * 480
    write_png(hstack(t3, upscale(crop(meadow, 60, 240, 160, 160), 3)), out / "compare_target_3x.png")
    write_png(upscale(crop(meadow, 50, 160, 260, 320), 3), out / "ingame_meadow_3x.png")
    write_png(upscale(crop(cavern, 50, 160, 260, 320), 3), out / "ingame_cave_3x.png")
    # heroes close-up: idle / walk / attack hit / hurt / cast frames at 6x
    order = ("warrior", "mage", "healer", "archer", "hunter")
    cols = [(0, 0), (1, 1), (2, 2), (5, 1), (4, 5)]
    close = Canvas(len(cols) * 34, len(order) * 33)
    for ri, k in enumerate(order):
        for ci, (row, col) in enumerate(cols):
            close.blit(sheet_frame(sheets[k], 32, 32, row, col), ci * 34, ri * 33)
    preview_pair(close, grass, 5, out / "heroes_closeup.png")
    # enemies close-up
    en = Canvas(5 * 26 + 66, 64)
    for i, k in enumerate(("goblin", "wolf", "skeleton", "slime", "wolf_companion")):
        en.blit(sheet_frame(sheets[k], 24, 24, 0, 0), i * 26, 38)
        en.blit(sheet_frame(sheets[k], 24, 24, 2, 2), i * 26, 12)
    en.blit(sheet_frame(sheets["boss"], 64, 64, 0, 0), 5 * 26 + 2, 0)
    preview_pair(en, grass, 4, out / "enemies_closeup.png")
    # small things
    misc = Canvas(10 * 12 + 32 + 64 * 3 + 12, 64)
    x = 0
    for key in ("arrow", "bolt", "arcane_bolt", "holy_bolt", "knife", "coin"):
        misc.blit(singles[key], x, 0)
        x += 10
    for key in ("potion", "sword"):
        misc.blit(singles[key], x, 12)
        x += 18
    misc.blit(singles["slash"], 0, 30)
    for i, key in enumerate(("nova", "arcane_blast", "heal_wave")):
        misc.blit(singles[key], 100 + i * 66, 0)
    preview_pair(misc, grass, 3, out / "items_vfx.png")
    # HUD icons on a dark button and stat icons in a dark pill
    ic = Canvas(26 * 6 + 18 * 4 + 8, 24)
    for i, cv in enumerate(icons.values()):
        ic.blit(cv, i * 26, 0)
    for i, cv in enumerate(stat_icons.values()):
        ic.blit(cv, 26 * 6 + 8 + i * 18, 4)
    btn = Canvas(1, 1)
    btn.px[0][0] = "k"
    preview_pair(ic, btn, 5, out / "hud_icons.png")
    # decor
    names = ("fir_tree", "bush", "rock", "stump", "log", "flowers", "mushroom", "ruin_pillar",
             "bones", "crystal", "stalagmite", "cave_rubble")
    dc = Canvas(sum(decor[n].w + 4 for n in names), 48)
    x = 0
    for n in names:
        dc.blit(decor[n], x, 48 - decor[n].h)
        x += decor[n].w + 4
    preview_pair(dc, grass, 4, out / "decor.png")
    dl = Canvas(48 + 32 + 8 + 56, 32)
    dl.blit(decor["dirt_patch"], 0, 0)
    dl.blit(decor["grass_patch"], 56, 4)
    dl.blit(decor["cave_dirt_patch"], 96, 0)
    write_png(hstack(upscale(compose(dl, grass, None), 4), upscale(compose(dl, cave, None), 4)), out / "decals.png")
    # ground tiles 3x3 at 2x (seams) side by side
    tiles = []
    for t in (grass, cave):
        big = Canvas(192, 192)
        for ty in range(3):
            for tx in range(3):
                big.blit(t, tx * 64, ty * 64)
        tiles.append(upscale(to_rgba(big), 2))
    write_png(hstack(*tiles), out / "tiles.png")


# ======================================================================================
def main() -> None:
    preview_dir = None
    if "--preview" in sys.argv:
        preview_dir = Path(sys.argv[sys.argv.index("--preview") + 1])
        preview_dir.mkdir(parents=True, exist_ok=True)

    sheets = {
        "warrior": (warrior_sheet_v3(), "sprites/characters/warrior.png"),
        "goblin": (goblin_sheet(), "sprites/enemies/goblin.png"),
        "wolf": (wolf_sheet(), "sprites/enemies/wolf.png"),
        "skeleton": (skeleton_sheet(), "sprites/enemies/skeleton.png"),
        "slime": (slime_sheet(), "sprites/enemies/slime.png"),
        "boss": (guardian_sheet(), "sprites/enemies/forest_guardian.png"),
        "mage": (mage_sheet_v3(), "sprites/characters/mage.png"),
        "healer": (healer_sheet_v3(), "sprites/characters/healer.png"),
        "archer": (archer_sheet_v3(), "sprites/characters/archer.png"),
        "hunter": (hunter_sheet_v3(), "sprites/characters/hunter.png"),
        "wolf_companion": (wolf_companion_sheet(), "sprites/companions/wolf_companion.png"),
    }
    for sh, rel in sheets.values():
        save(sh, rel)
    singles = {
        "arrow": (arrow_sprite(), "sprites/projectiles/arrow.png"),
        "bolt": (bolt_sprite(), "sprites/projectiles/bolt.png"),
        "potion": (potion_icon(), "sprites/items/health_potion.png"),
        "sword": (sword_icon(), "sprites/items/iron_sword.png"),
        "coin": (coin_icon(), "sprites/items/gold_coin.png"),
        "slash": (slash_vfx(), "sprites/vfx/slash.png"),
        "nova": (nova_vfx(), "sprites/vfx/nova.png"),
        "arcane_bolt": (arcane_bolt_sprite(), "sprites/projectiles/arcane_bolt.png"),
        "holy_bolt": (holy_bolt_sprite(), "sprites/projectiles/holy_bolt.png"),
        "knife": (knife_sprite(), "sprites/projectiles/knife.png"),
        "arcane_blast": (arcane_blast_vfx(), "sprites/vfx/arcane_blast.png"),
        "heal_wave": (heal_wave_vfx(), "sprites/vfx/heal_wave.png"),
        "grass": (grass_tile(), "tilesets/grass.png"),
        "cave": (cave_tile(), "tilesets/cave.png"),
    }
    for cv, rel in singles.values():
        save(cv, rel)
    icons = {"attack": icon_attack(), "skill": icon_skill(), "dash": icon_dash(), "bag": icon_bag(),
             "use": icon_use(), "pause": icon_pause()}
    for name, cv in icons.items():
        save(cv, f"ui/hud_icons/{name}.png")
    stat_icons = {"gold": stat_gold(), "kills": stat_kills(), "timer": stat_timer(), "level": stat_level()}
    for name, cv in stat_icons.items():
        save(cv, f"ui/hud_icons/{name}.png")
    decor = {"fir_tree": fir_tree(), "bush": bush(), "rock": rock(), "stump": stump(), "log": log(),
             "flowers": flowers(), "mushroom": mushroom(), "ruin_pillar": ruin_pillar(),
             "dirt_patch": dirt_patch(), "grass_patch": grass_patch(),
             "bones": bones(), "crystal": crystal(), "stalagmite": stalagmite(), "cave_rubble": cave_rubble(),
             "cave_dirt_patch": cave_dirt_patch()}
    for name, cv in decor.items():
        save(cv, f"sprites/decor/{name}.png")

    # every written pixel must come from the master palette (keys are checked by RGBA lookup)
    names = {}
    for key, hx in PALETTE.items():
        names.setdefault(hx, []).append(key)
    gpl = ["GIMP Palette", "Name: Pixel Fantasy Survival master v2", "Columns: 8", "#"]
    for hx in UNIQUE_COLOURS:
        gpl.append(f"{int(hx[0:2], 16):3d} {int(hx[2:4], 16):3d} {int(hx[4:6], 16):3d}\t"
                   f"{'/'.join(names[hx])} #{hx}")
    pal_path = REPO / "docs" / "art" / "source" / "master_palette.gpl"
    pal_path.parent.mkdir(parents=True, exist_ok=True)
    pal_path.write_text("\n".join(gpl) + "\n", encoding="utf-8")

    for rel, w, h in WRITTEN:
        print(f"  {rel}  {w}x{h}")
    print(f"  palette ({len(UNIQUE_COLOURS)} colours) -> {pal_path.relative_to(REPO)}")

    if preview_dir:
        write_previews(preview_dir, {k: v[0] for k, v in sheets.items()}, {k: v[0] for k, v in singles.items()},
                       icons, stat_icons, decor)
        print(f"previews -> {preview_dir}")


if __name__ == "__main__":
    main()
