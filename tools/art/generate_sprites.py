#!/usr/bin/env python3
"""Pixel Fantasy Survival - procedural pixel-art generator (P0 art set).

Everything is drawn pixel by pixel at native resolution from one master
palette (38 colours) and written as PNG with zlib + struct (stdlib only).

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
# Master palette (32 colours). Derived from docs/art/palette.json + the key art
# (warrior leather/rust fur, steel, bronze, forest greens, lake blues) + ui_kit.gd.
# One character per colour so parts can be drawn as ASCII pixel maps.
# --------------------------------------------------------------------------------------
PALETTE: dict[str, str] = {
    "o": "15110e",  # outline, dark warm
    "k": "2a221b",  # deepest brown (shadows, shield wood)
    "a": "3d2a1c",  # leather 1 (dark)
    "b": "5c3d25",  # leather 2
    "c": "84573a",  # leather 3
    "d": "a87a4f",  # leather 4 (light)
    "e": "6b3218",  # rust fur 1
    "f": "a4552a",  # rust fur 2
    "g": "d4894a",  # rust fur 3
    "h": "8a5a3c",  # skin 1
    "i": "c48a62",  # skin 2
    "j": "ebbd92",  # skin 3
    "m": "3a3d47",  # steel / stone 1
    "n": "6a7380",  # steel / stone 2
    "p": "a5afb8",  # steel / stone 3
    "q": "7a5a2c",  # bronze 1
    "r": "d9a441",  # gold 2
    "s": "f7e09a",  # gold 3
    "t": "1d2f22",  # forest 1 (darkest)
    "u": "2e4a2f",  # forest 2 (grass base)
    "v": "45683a",  # forest 3
    "w": "6d9446",  # forest 4
    "x": "a8c85c",  # forest 5 / spore glow
    "y": "8f8570",  # bone 1
    "z": "d3cab0",  # bone 2
    "W": "f2ead8",  # parchment white (highlights, VFX)
    "R": "6e2020",  # blood red 1
    "S": "b8453a",  # red 2 (ui_kit HEALTH)
    "A": "2f4f72",  # lake blue 1
    "B": "5588bb",  # lake blue 2 (ui_kit XP)
    "C": "9fd0ea",  # lake blue 3
    "D": "221f27",  # cave dark
    # ground-only tones: deliberately close to their neighbours so floors stay calm
    "G": "28422b",  # grass ground shade (next to u)
    "H": "33363f",  # cave ground shade (next to m)
    # arcane purple ramp (mage robe, arcane bolt / blast) - added with the playable mage
    "K": "241a33",  # purple 1 (darkest)
    "L": "3b2c58",  # purple 2
    "M": "5f4a8e",  # purple 3
    "N": "a48ad8",  # violet glow
}
assert len(PALETTE) == 38  # 32 sprite colours + 2 low-contrast ground tones + 4 arcane purples
RGBA = {k: (int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16), 255) for k, v in PALETTE.items()}

# Ramps: one step darker / lighter inside the same material.
DARKER = {"d": "c", "c": "b", "b": "a", "a": "k", "k": "o", "g": "f", "f": "e", "e": "k",
          "j": "i", "i": "h", "h": "e", "p": "n", "n": "m", "m": "D", "D": "o", "s": "r", "r": "q",
          "q": "a", "x": "w", "w": "v", "v": "u", "u": "t", "t": "o", "G": "t", "H": "D", "z": "y", "y": "n", "W": "z",
          "S": "R", "R": "k", "C": "B", "B": "A", "A": "D", "o": "o",
          "N": "M", "M": "L", "L": "K", "K": "o"}
LIGHTER = {"o": "k", "k": "a", "a": "b", "b": "c", "c": "d", "d": "j", "e": "f", "f": "g", "g": "s",
           "h": "i", "i": "j", "j": "W", "D": "m", "m": "n", "n": "p", "p": "W", "q": "r", "r": "s",
           "s": "W", "t": "u", "G": "u", "H": "m", "u": "v", "v": "w", "w": "x", "x": "s", "y": "z", "z": "W", "W": "W",
           "R": "S", "S": "g", "A": "B", "B": "C", "C": "W",
           "K": "L", "L": "M", "M": "N", "N": "W"}

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
# WARRIOR 32x32  (brown leather, rusty fur collar, steel sword, round dark shield)
# ======================================================================================
W_FOOT = 30  # bottom row of the boots

HEAD = [
    "...bcccb..",
    "..bcddddc.",
    ".bcddcccdb",
    "bcdcbbiijb",
    "bccbhijjji",
    "bcbhijjoji",
    "bbbhiijjjj",
    ".bahiiiih.",
    ".abefgffe.",
    "..aeggfe..",
    "...eeee...",
]

TORSO = [
    "...........",
    ".bcdddccba.",
    "bcddcccrbba",
    "bcdcccrcbba",
    "bcccbrccbba",
    "bccbrcccbba",
    "abcrcccbbaa",
    "aqrqqqsrqqa",
    ".abbbbbbaa.",
    ".abbcbbbaa.",
]

COLLAR = [
    "..gggg.ggg...",
    ".ggfgggfgggf.",
    "gfgffgfffgffe",
    "effefffefffe.",
    ".e.eee.ee.e..",
]

LEG = [
    "abb",
    "abb",
    "abc",
    "abb",
    "kab",
    "bccb",
    "bcdcb",
    "abbbbb",
]


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


def draw_shield(c: Canvas, cx: float, cy: float) -> None:
    c.ellipse(cx, cy, 4.6, 5.6, "m")
    c.ellipse(cx + 0.3, cy + 0.2, 3.6, 4.6, "k")
    # rim highlight top-left
    for (x, y) in ((-3, -4), (-2, -5), (-4, -2), (-4, -1), (-1, -5)):
        c.set(cx + x, cy + y, "n")
    c.set(cx - 2, cy - 4, "p")
    # wood shading
    for y in range(-3, 4):
        c.set(cx + 2, cy + y, "a")
    c.set(cx - 2, cy - 2, "a")
    # emblem: pale tree / star
    for (x, y, col) in ((0, -3, "z"), (0, -2, "W"), (-1, -1, "z"), (0, -1, "W"), (1, -1, "z"),
                        (0, 0, "r"), (-2, 0, "z"), (2, 0, "y"), (0, 1, "W"), (-1, 2, "z"), (1, 2, "y"),
                        (0, 2, "z")):
        c.set(cx + x, cy + y, col)


def warrior(bob: int = 0, back_dx: int = 0, back_lift: int = 0, front_dx: int = 0, front_lift: int = 0,
            hand: tuple[float, float] = (10, 21), sword: float = 112, sword_front: bool = False,
            shield_dx: int = 0, shield_dy: int = 0, lean: int = 0, crouch: int = 0,
            blink: bool = False, fx: str | None = None) -> Canvas:
    c = Canvas(32, 32)
    ub = bob + crouch  # upper body offset
    lx = lean
    # back leg (darker)
    dark = DARKER
    c.stamp(LEG, 12 + back_dx, 23 - back_lift + max(0, crouch - 1), remap=dark)
    # sword arm + sword behind body
    sx, sy = 12 + lx, 15 + ub
    hx, hy = hand[0] + lx, hand[1] + ub
    if not sword_front:
        draw_sword(c, hx, hy, sword)
    c.line(sx, sy, hx, hy, "b")
    c.line(sx + 1, sy, hx + 1 if hx >= sx else hx - 0, hy, "c")
    c.set(hx, hy, "i")
    # torso
    c.stamp(TORSO, 10 + lx, 13 + ub)
    # front leg
    c.stamp(LEG, 16 + front_dx, 23 - front_lift + max(0, crouch - 1))
    # collar and head
    c.stamp(COLLAR, 9 + lx, 11 + ub)
    head = list(HEAD)
    if blink:
        head[5] = "bcbiijjhj."
    c.stamp(head, 11 + lx, 2 + ub)
    # shield arm + shield (front)
    draw_shield(c, 22 + lx + shield_dx, 18 + ub + shield_dy)
    if sword_front:
        draw_sword(c, hx, hy, sword)
        c.set(hx, hy, "i")
        c.set(hx - 1, hy, "c")
    if fx == "slam":
        for (x, y, col) in ((23, 30, "W"), (29, 30, "W"), (22, 28, "z"), (30, 28, "z"), (21, 26, "W"),
                            (30, 25, "W"), (24, 27, "W"), (28, 27, "z")):
            c.set(x, y, col)
    return c


def warrior_sheet() -> Canvas:
    F = finish
    idle = [F(warrior(bob=b, blink=(i == 3))) for i, b in enumerate((0, 0, 1, 1))]
    walk = []
    for f in range(6):
        p = f / 6 * 2 * math.pi
        s = math.sin(p)
        fd = round(2.4 * s)
        bd = -fd
        fl = 1 if math.cos(p) > 0.5 else 0
        bl = 1 if math.cos(p) < -0.5 else 0
        bob = 0 if abs(s) > 0.6 else 1
        walk.append(F(warrior(bob=bob, front_dx=fd, back_dx=bd, front_lift=fl, back_lift=bl,
                              hand=(10 - fd // 2, 21), sword=112 + fd * 4)))
    attack = [
        F(warrior(hand=(10, 15), sword=200, lean=-1, back_dx=-1, front_dx=1)),
        F(warrior(hand=(12, 11), sword=250, bob=-1, back_dx=-1, front_dx=1)),
        F(warrior(hand=(21, 15), sword=5, sword_front=True, lean=1, shield_dx=-2, shield_dy=2,
                  back_dx=-2, front_dx=2)),
        F(warrior(hand=(21, 19), sword=55, sword_front=True, lean=1, shield_dx=-2, shield_dy=2,
                  back_dx=-2, front_dx=2)),
        F(warrior(hand=(13, 20), sword=100, back_dx=-1, front_dx=1)),
    ]
    hurt = [F(flash(warrior(lean=-1, shield_dx=-1, hand=(9, 20)))), F(warrior(lean=-1, hand=(9, 20)))]
    pose = dict(hand=(9, 21), sword=90, lean=-1)
    death = fall_frames(warrior, pose, W_FOOT, 15, [-35, -70, -90, -90], 32, 32,
                        pre=[F(flash(warrior(lean=-1, hand=(9, 20)))), F(warrior(crouch=2, lean=-1, hand=(9, 22), sword=150))])
    # settle: last frame lowered sword lying beside
    cast = [
        F(warrior(hand=(25, 13), sword=270, sword_front=True, shield_dx=-2)),
        F(warrior(hand=(25, 12), sword=270, sword_front=True, bob=-1, shield_dx=-2, front_dx=1, back_dx=-1)),
        F(warrior(hand=(26, 17), sword=90, sword_front=True, crouch=2, shield_dx=-4, back_dx=-2, front_dx=2)),
        F(warrior(hand=(26, 17), sword=90, sword_front=True, crouch=2, shield_dx=-4, back_dx=-2, front_dx=2,
                  fx="slam")),
    ]
    return build_sheet([idle, walk, attack, hurt, death, cast], 32, 32)


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
    for _ in range(9):
        x = rnd.randint(cx - 9, cx + 9)
        y = rnd.randint(36, 49)
        for k in range(rnd.randint(3, 6)):
            c.set(x, y + k + ub, "k")
            c.set(x - 1, y + k + ub, "d" if x < cx else "c")
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
        c.set(x, 40 + ub - (k % 2), "o")
    c.set(cx - 1, 38 + ub, "t")
    # crown: big leaf clumps, darker underneath, bumpy edge
    clumps = [(18, 20, 7, 6), (46, 20, 7, 6), (32, 10, 11, 8), (22, 12, 7, 6), (42, 12, 7, 6),
              (25, 21, 7, 5), (39, 21, 7, 5), (32, 19, 9, 6), (14, 25, 4, 3), (50, 25, 4, 3),
              (27, 4, 4, 3), (37, 4, 4, 3), (13, 17, 4, 4), (51, 17, 4, 4)]
    for (x, y, rx, ry) in clumps:
        c.shaded_ellipse(x + L + sway, y + ub, rx, ry, "tuvwx", bias=-0.08)
    # leaf texture: little dark notches + light flecks
    for (x, y, col) in ((24, 8, "x"), (30, 6, "x"), (36, 8, "w"), (20, 15, "x"), (44, 15, "w"),
                        (28, 15, "t"), (37, 16, "t"), (17, 21, "u"), (47, 22, "t"), (32, 13, "x")):
        c.set(x + L + sway, y + ub, col)
    # glowing spore pods
    for (x, y) in ((26, 12), (38, 6), (45, 17), (19, 22), (33, 17), (41, 23)):
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
# PLAYABLE HEROES 32x32: mage, healer, archer, hunter (exactly the warrior layout)
# Same construction as the warrior: parts stamped from ASCII maps, posed by parameters,
# drawn on the foot row H_FOOT (=W_FOOT), outlined by finish(), lifted 1 px by build_sheet.
# ======================================================================================
H_FOOT = 30


def robe(c: Canvas, cx: float, top: int, bottom: int, hw0: float, hw1: float, ramp: str,
         lean: int = 0, sway: float = 0.0, power: float = 1.4) -> dict[int, tuple[int, int]]:
    """Bell-shaped robe lit from the left. ramp = dark, mid, lit. Returns row extents."""
    rows = {}
    for y in range(top, bottom + 1):
        t = (y - top) / max(1, bottom - top)
        hw = hw0 + (hw1 - hw0) * t ** power
        mid = cx + lean * (1 - t) + sway * t
        x0, x1 = round(mid - hw), round(mid + hw)
        for x in range(x0, x1 + 1):
            u = (x - x0) / max(1, x1 - x0)
            c.set(x, y, ramp[2] if u < 0.28 else (ramp[1] if u < 0.7 else ramp[0]))
        rows[y] = (x0, x1)
    return rows


def sleeve(c: Canvas, sx: float, sy: float, hx: float, hy: float, dark: str, lit: str,
           cuff: str | None = None, hand: str = "i") -> None:
    """Two-pixel arm from shoulder to hand; cuff colour right before the hand."""
    c.line(sx, sy, hx, hy, dark)
    c.line(sx, sy - 1, hx, hy - 1, lit)
    if cuff:
        L = max(1.0, math.hypot(hx - sx, hy - sy))
        ux, uy = (hx - sx) / L, (hy - sy) / L
        c.set(round(hx - ux * 1.2), round(hy - uy * 1.2), cuff)
        c.set(round(hx - ux * 1.2), round(hy - uy * 1.2) - 1, cuff)
    c.set(hx, hy, hand)


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


def robe_feet(c: Canvas, cx: int, front_dx: int, back_dx: int, front_lift: int, back_lift: int,
              col: str = "b", dark: str = "a") -> None:
    """Boot toes peeking out under a robe hem (foot row H_FOOT)."""
    bx = cx - 3 + back_dx
    c.rect(bx, H_FOOT - back_lift, 3, 1, dark)
    c.set(bx + 3, H_FOOT - back_lift, "k")
    fx = cx + 1 + front_dx
    c.rect(fx, H_FOOT - front_lift, 4, 1, col)
    c.set(fx, H_FOOT - front_lift, dark)
    c.set(fx + 3, H_FOOT - 1 - front_lift, col)


# ---------------------------------------------------------------- MAGE
# dark purple robe with gold trim, high collar, long dark hair and beard, staff with blue crystal
MAGE_HEAD = [
    "...kaaak..",
    "..kaabaak.",
    ".kabaaaabk",
    "kaakkkiijk",
    "kaakhijjji",
    "kaahijjoji",
    "kakhiijjjj",
    "kakhiiiih.",
    "kak.aaaaa.",
    "kk..akaak.",
    "......aa..",
]
MAGE_COLLAR = [
    "LL.......",
    "MLL......",
    "MLLL.....",
    "rMLLr....",
]


def mage(bob: int = 0, front_dx: int = 0, back_dx: int = 0, front_lift: int = 0, back_lift: int = 0,
         hand: tuple[float, float] = (22, 19), staff: float = -90, staff_up: float = 15, staff_down: float = 10,
         back_hand: tuple[float, float] | None = None, lean: int = 0, crouch: int = 0, sway: float = 0,
         glow: int = 0, blink: bool = False, fx: str | None = None) -> Canvas:
    c = Canvas(32, 32)
    ub = bob + crouch
    lx = lean
    cx = 15
    # back arm raised (cast) is behind the body
    if back_hand:
        sleeve(c, cx - 1 + lx, 16 + ub, back_hand[0] + lx, back_hand[1] + ub, "K", "L", cuff="r")
    robe_feet(c, cx, front_dx, back_dx, front_lift, back_lift, col="b", dark="a")
    rows = robe(c, cx + 0.5, 14 + ub, 29, 4.0, 7.6, "KLM", lean=lx, sway=sway)
    # gold hem and front opening
    for y in (28, 29):
        x0, x1 = rows[y]
        for x in range(x0, x1 + 1):
            if y == 28:
                c.set(x, y, "r" if x < x1 - 2 else "q")
    for y in range(20 + ub, 28):
        x0, x1 = rows[y]
        ox = x0 + round((x1 - x0) * 0.66)
        c.set(ox, y, "r" if y % 3 else "s")
        c.set(ox + 1, y, "K")
    # belt + pouch + crossed straps + blue amulet
    yb = 20 + ub
    x0, x1 = rows[yb]
    for x in range(x0, x1 + 1):
        c.set(x, yb, "b" if x < x1 - 1 else "a")
    c.set(cx + 1 + lx, yb, "r")
    c.rect(cx + 3 + lx, yb + 1, 2, 2, "c")
    c.set(cx + 3 + lx, yb + 1, "d")
    c.line(cx - 2 + lx, 15 + ub, cx + 2 + lx, 19 + ub, "a")
    c.set(cx + lx, 16 + ub, "B")
    c.set(cx + lx, 15 + ub, "r")
    # high collar behind the head
    c.stamp(MAGE_COLLAR, cx - 6 + lx, 10 + ub)
    head = list(MAGE_HEAD)
    if blink:
        head[5] = "kaahiijjhi"
    c.stamp(head, cx - 4 + lx, 4 + ub)
    # staff + front sleeve (wide, purple, gold cuff)
    hx, hy = hand[0] + lx, hand[1] + ub
    tx, ty = draw_staff(c, hx, hy, staff, staff_up, staff_down)
    sleeve(c, cx + 2 + lx, 16 + ub, hx, hy, "L", "M", cuff="r")
    c.set(cx + 2 + lx, 17 + ub, "L")
    c.set(cx + 3 + lx, 17 + ub, "L")
    if back_hand:
        c.set(back_hand[0] + lx, back_hand[1] + ub, "i")
    draw_crystal(c, tx, ty, glow)
    if fx == "spark":
        for (dx, dy, col) in ((3, 0, "W"), (5, 0, "N"), (4, -2, "C"), (4, 2, "C")):
            c.set(tx + dx, ty + dy, col)
    if fx == "ground":
        for (x, y, col) in ((6, 29, "N"), (9, 27, "C"), (25, 28, "N"), (28, 26, "C"), (12, 24, "W"), (27, 22, "W")):
            c.set(x, y, col)
    return c


def mage_sheet() -> Canvas:
    F = finish
    idle = [F(mage(bob=b, blink=(i == 3), staff_up=15 - b)) for i, b in enumerate((0, 0, 1, 1))]
    walk = []
    for f in range(6):
        p = f / 6 * 2 * math.pi
        s = math.sin(p)
        fd = round(1.6 * s)
        bob = 0 if abs(s) > 0.6 else 1
        walk.append(F(mage(bob=bob, front_dx=fd, back_dx=-fd, front_lift=0, back_lift=0, sway=-s * 0.8,
                           hand=(22 + fd // 2, 19), staff=-90 + fd * 3, staff_up=15 - bob)))
    attack = [
        F(mage(hand=(19, 18), staff=-110, staff_up=13, staff_down=9, lean=-1, glow=1)),
        F(mage(hand=(20, 17), staff=-70, staff_up=13, staff_down=8, glow=1, back_dx=-1, front_dx=1)),
        F(mage(hand=(24, 17), staff=-40, staff_up=8, staff_down=8, lean=1, glow=2, fx="spark",
               back_dx=-2, front_dx=2)),
        F(mage(hand=(24, 17), staff=-45, staff_up=8, staff_down=8, lean=1, glow=1, back_dx=-2, front_dx=2)),
        F(mage(hand=(22, 18), staff=-80, staff_up=14, staff_down=10, back_dx=-1, front_dx=1)),
    ]
    hurt = [F(flash(mage(lean=-1, hand=(21, 19), staff=-100))), F(mage(lean=-1, hand=(21, 19), staff=-100))]
    pose = dict(hand=(21, 20), staff=-110, lean=-1)
    death = fall_frames(mage, pose, H_FOOT, 15, [-35, -70, -90, -90], 32, 32,
                        pre=[F(flash(mage(lean=-1, hand=(21, 19), staff=-100))),
                             F(mage(crouch=2, lean=-1, hand=(21, 21), staff=-115, staff_down=5, staff_up=17))])
    cast = [
        F(mage(hand=(21, 16), staff=-90, staff_up=12, staff_down=10, back_hand=(19, 15), glow=1)),
        F(mage(hand=(21, 13), staff=-90, staff_up=9, staff_down=11, back_hand=(19, 12), glow=2, bob=-1)),
        F(mage(hand=(21, 13), staff=-90, staff_up=9, staff_down=11, back_hand=(19, 12), glow=2, bob=-1,
               fx="ground")),
        F(mage(hand=(21, 16), staff=-90, staff_up=12, staff_down=10, back_hand=(18, 16), glow=1)),
    ]
    return build_sheet([idle, walk, attack, hurt, death, cast], 32, 32)


# ---------------------------------------------------------------- HEALER
# white robe with a green front panel, green hooded mantle, dark curly hair, gold staff with green cross
HEALER_HEAD = [
    "..kaabak..",
    ".kaabcaak.",
    "kabbaabbak",
    "kaabakijak",
    "kbakhijjjk",
    "kakhijjoj.",
    "kakhiijjj.",
    "kbakhiiih.",
    "kak.hii...",
    ".k........",
]
HEALER_MANTLE = [
    "....uuuu....",
    "..uvvwwvvu..",
    ".uvwwwvvvuu.",
    "tuvwvvvvvuut",
    "tuvvvvvvuut.",
    "tuuvvuuuut..",
    "tuuuuttt....",
    "tuuut.......",
    "ttu.........",
]


def healer(bob: int = 0, front_dx: int = 0, back_dx: int = 0, front_lift: int = 0, back_lift: int = 0,
           hand: tuple[float, float] = (21, 19), staff: float = -90, staff_up: float = 14, staff_down: float = 10,
           back_hand: tuple[float, float] | None = None, lean: int = 0, crouch: int = 0, sway: float = 0,
           glow: int = 0, blink: bool = False, fx: str | None = None) -> Canvas:
    c = Canvas(32, 32)
    ub = bob + crouch
    lx = lean
    cx = 15
    robe_feet(c, cx, front_dx, back_dx, front_lift, back_lift, col="c", dark="b")
    rows = robe(c, cx + 0.5, 15 + ub, 29, 3.6, 6.4, "yzW", lean=lx, sway=sway, power=1.2)
    # green front panel with gold stitch, green hem
    for y in range(21 + ub, 30):
        x0, x1 = rows[y]
        ox = x0 + round((x1 - x0) * 0.58)
        c.set(ox, y, "v")
        c.set(ox + 1, y, "u")
        if y % 3 == 0:
            c.set(ox, y, "r")
    x0, x1 = rows[29]
    for x in range(x0, x1 + 1):
        c.set(x, 29, "v" if x < x1 - 2 else "u")
    # gold belt + brown pouch
    yb = 21 + ub
    x0, x1 = rows[yb]
    for x in range(x0, x1 + 1):
        c.set(x, yb, "r" if x < x1 - 1 else "q")
    c.rect(cx - 3 + lx, yb + 1, 2, 2, "c")
    c.set(cx - 3 + lx, yb + 1, "d")
    # green hooded mantle over the shoulders
    c.stamp(HEALER_MANTLE, cx - 7 + lx, 12 + ub)
    c.set(cx + 1 + lx, 15 + ub, "r")
    if back_hand:  # raised back arm shows beside the head
        sleeve(c, cx - 2 + lx, 15 + ub, back_hand[0] + lx, back_hand[1] + ub, "y", "z", cuff="v")
    head = list(HEALER_HEAD)
    if blink:
        head[5] = "kabhiijji."
    c.stamp(head, cx - 4 + lx, 5 + ub)
    hx, hy = hand[0] + lx, hand[1] + ub
    tx, ty = draw_staff(c, hx, hy, staff, staff_up, staff_down, shaft="q", hi="r")
    sleeve(c, cx + 2 + lx, 16 + ub, hx, hy, "z", "W", cuff="v")
    if back_hand:
        c.set(back_hand[0] + lx, back_hand[1] + ub, "i")
    draw_cross(c, tx, ty, glow)
    if fx == "spark":
        for (dx, dy, col) in ((3, 0, "W"), (5, 0, "s"), (4, -2, "x"), (4, 2, "x")):
            c.set(tx + dx, ty + dy, col)
    if fx == "light":
        for (x, y, col) in ((5, 8, "s"), (8, 3, "W"), (26, 4, "s"), (11, 1, "s"), (27, 10, "W"), (4, 14, "W")):
            c.set(x, y, col)
    return c


def healer_sheet() -> Canvas:
    F = finish
    idle = [F(healer(bob=b, blink=(i == 3), staff_up=14 - b)) for i, b in enumerate((0, 0, 1, 1))]
    walk = []
    for f in range(6):
        p = f / 6 * 2 * math.pi
        s = math.sin(p)
        fd = round(1.6 * s)
        bob = 0 if abs(s) > 0.6 else 1
        walk.append(F(healer(bob=bob, front_dx=fd, back_dx=-fd, sway=-s * 0.8,
                             hand=(21 + fd // 2, 19), staff=-90 + fd * 3, staff_up=14 - bob)))
    attack = [
        F(healer(hand=(19, 18), staff=-105, staff_up=12, lean=-1, glow=1)),
        F(healer(hand=(21, 17), staff=-65, staff_up=12, staff_down=8, glow=1, back_dx=-1, front_dx=1)),
        F(healer(hand=(24, 17), staff=-30, staff_up=7, staff_down=8, lean=1, glow=2, fx="spark",
                 back_dx=-2, front_dx=2)),
        F(healer(hand=(24, 17), staff=-35, staff_up=7, staff_down=8, lean=1, glow=1, back_dx=-2, front_dx=2)),
        F(healer(hand=(21, 18), staff=-80, staff_up=13, back_dx=-1, front_dx=1)),
    ]
    hurt = [F(flash(healer(lean=-1, hand=(20, 19), staff=-100))), F(healer(lean=-1, hand=(20, 19), staff=-100))]
    pose = dict(hand=(20, 20), staff=-110, lean=-1)
    death = fall_frames(healer, pose, H_FOOT, 15, [-35, -70, -90, -90], 32, 32,
                        pre=[F(flash(healer(lean=-1, hand=(20, 19), staff=-100))),
                             F(healer(crouch=2, lean=-1, hand=(20, 21), staff=-115, staff_down=5, staff_up=16))])
    cast = [
        F(healer(hand=(21, 15), staff=-90, staff_up=11, back_hand=(9, 12), glow=1)),
        F(healer(hand=(21, 11), staff=-90, staff_up=8, staff_down=12, back_hand=(8, 7), glow=2, bob=-1)),
        F(healer(hand=(21, 11), staff=-90, staff_up=8, staff_down=12, back_hand=(8, 7), glow=2, bob=-1,
                 fx="light")),
        F(healer(hand=(21, 15), staff=-90, staff_up=11, back_hand=(9, 13), glow=1)),
    ]
    return build_sheet([idle, walk, attack, hurt, death, cast], 32, 32)


# ---------------------------------------------------------------- shared bow (any tilt)
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


# ---------------------------------------------------------------- ARCHER
# short brown hair, green cowl and cloak, leather jerkin, quiver with pale fletchings, longbow
ARCHER_HEAD = [
    "...bccb...",
    "..bccdccb.",
    ".bcdccbccb",
    "abccbaiijb",
    "abahijjjji",
    "abahijjoji",
    ".bbhiijjjj",
    "..bhiiiih.",
    "...hhii...",
]
ARCHER_COWL = [
    "..vwwv.vvu...",
    ".vwwvvwvvvuu.",
    "uvwvvvvvvvuut",
    "tuuvuuuvuut..",
]
ARCHER_TORSO = [
    "...........",
    ".bcddcccba.",
    "bcddccacbba",
    "bcdccacbbba",
    "bcccacccbba",
    "bccacccbbba",
    "abacccccbaa",
    "aaarqaaaaaa",
    ".tuuuuuuut.",
    ".tuuvuuuut.",
]
ARCHER_LEG = [
    "tuu",
    "tuu",
    "tuv",
    "acc",
    "bcd",
    "bccb",
    "bcdcb",
    "abbbbb",
]


def archer_cloak(c: Canvas, lx: int, ub: int, flutter: int = 0) -> None:
    """Green cloak hanging behind the back shoulder."""
    for y in range(13 + ub, 27):
        k = y - 13 - ub
        x0 = round(10 + lx - k * 0.32 - (flutter if k > 6 else 0))
        x1 = 14 + lx
        for x in range(x0, x1 + 1):
            c.set(x, y, "v" if x == x0 and k < 7 else ("u" if x < x0 + 3 else "t"))
    # ragged hem
    for i, x in enumerate(range(round(10 + lx - 13 * 0.32 - flutter), 15 + lx)):
        if i % 3 == 1:
            c.set(x, 27, "t")


def archer(bob: int = 0, back_dx: int = 0, back_lift: int = 0, front_dx: int = 0, front_lift: int = 0,
           grip: tuple[float, float] = (23, 19), tilt: float = 0, draw: float = 0, arrow: bool = False,
           pull: tuple[float, float] | None = None, lean: int = 0, crouch: int = 0, flutter: int = 0,
           blink: bool = False, fx: str | None = None) -> Canvas:
    c = Canvas(32, 32)
    ub = bob + crouch
    lx = lean
    # quiver on the back: tube + fletchings above the back shoulder
    c.line(8 + lx, 19 + ub, 10 + lx, 10 + ub, "b")
    c.line(9 + lx, 19 + ub, 11 + lx, 10 + ub, "a")
    for (x, y, col) in ((8, 6, "W"), (9, 5, "z"), (10, 6, "W"), (11, 5, "z"), (7, 7, "z"), (9, 7, "S"),
                        (10, 8, "S"), (9, 8, "c"), (10, 9, "c")):
        c.set(x + lx, y + ub, col)
    archer_cloak(c, lx, ub, flutter)
    c.stamp(ARCHER_LEG, 12 + back_dx, 23 - back_lift, remap=DARKER)
    # drawing arm (behind the torso when relaxed)
    gx, gy = grip[0] + lx, grip[1] + ub
    if pull is None:
        pull_pt = (13 + lx, 21 + ub)
    else:
        pull_pt = (pull[0] + lx, pull[1] + ub)
    c.stamp(ARCHER_TORSO, 10 + lx, 13 + ub)
    c.stamp(ARCHER_LEG, 16 + front_dx, 23 - front_lift)
    c.stamp(ARCHER_COWL, 9 + lx, 11 + ub)
    head = list(ARCHER_HEAD)
    if blink:
        head[5] = "bcbhiijjhj"
    c.stamp(head, 11 + lx, 3 + ub)
    # bow + bow arm (front)
    nock = draw_longbow(c, gx, gy, tilt, draw, arrow)
    sleeve(c, 18 + lx, 15 + ub, gx - 1, gy, "b", "c", cuff="a")
    # string hand
    hand = nock if (draw or arrow) else pull_pt
    sleeve(c, 13 + lx, 15 + ub, hand[0], hand[1], "a", "b", hand="i")
    if fx == "release":
        t = math.radians(tilt)
        for k, col in ((4, "W"), (6, "z"), (8, "W")):
            c.set(round(gx + math.cos(t) * k), round(gy + math.sin(t) * k), col)
    if fx == "volley":
        for (x, y, col) in ((27, 6, "W"), (29, 9, "z"), (25, 3, "z"), (30, 4, "W")):
            c.set(x, y, col)
    return c


def archer_sheet() -> Canvas:
    F = finish
    idle = [F(archer(bob=b, blink=(i == 3))) for i, b in enumerate((0, 0, 1, 1))]
    walk = []
    for f in range(6):
        p = f / 6 * 2 * math.pi
        s = math.sin(p)
        fd = round(2.4 * s)
        fl = 1 if math.cos(p) > 0.5 else 0
        bl = 1 if math.cos(p) < -0.5 else 0
        bob = 0 if abs(s) > 0.6 else 1
        walk.append(F(archer(bob=bob, front_dx=fd, back_dx=-fd, front_lift=fl, back_lift=bl,
                             grip=(23 + fd // 2, 19), tilt=fd * 3, flutter=1 if bob else 0)))
    attack = [
        F(archer(grip=(24, 16), arrow=True, draw=1, back_dx=-1, front_dx=1)),
        F(archer(grip=(25, 16), arrow=True, draw=5, lean=-1, back_dx=-2, front_dx=2)),
        F(archer(grip=(25, 16), draw=0, pull=(15, 14), lean=-1, back_dx=-2, front_dx=2, fx="release")),
        F(archer(grip=(24, 17), draw=0, pull=(14, 16), back_dx=-1, front_dx=1)),
        F(archer(grip=(23, 18), back_dx=-1, front_dx=1)),
    ]
    hurt = [F(flash(archer(lean=-1, grip=(22, 19)))), F(archer(lean=-1, grip=(22, 19)))]
    pose = dict(grip=(21, 21), tilt=20, lean=-1)
    death = fall_frames(archer, pose, H_FOOT, 15, [-35, -70, -90, -90], 32, 32,
                        pre=[F(flash(archer(lean=-1, grip=(22, 19)))), F(archer(crouch=2, lean=-1, grip=(21, 18), tilt=15))])
    cast = [
        F(archer(grip=(24, 14), tilt=-30, arrow=True, draw=1, back_dx=-1, front_dx=1)),
        F(archer(grip=(24, 13), tilt=-45, arrow=True, draw=4, lean=-1, back_dx=-2, front_dx=2, flutter=1)),
        F(archer(grip=(24, 13), tilt=-45, draw=0, pull=(16, 14), lean=-1, back_dx=-2, front_dx=2, fx="volley",
                 flutter=1)),
        F(archer(grip=(24, 15), tilt=-30, arrow=True, draw=2, back_dx=-1, front_dx=1)),
    ]
    return build_sheet([idle, walk, attack, hurt, death, cast], 32, 32)


# ---------------------------------------------------------------- HUNTER
# fur-trimmed hood, khaki cloak, dark leather, throwing knives, bow slung on the back
HUNTER_HEAD = [
    "....aabba..",
    "...abcccba.",
    "..abccbbbba",
    ".abcbbbzWzz",
    ".abbbzWccij",
    "abbbbzhijjj",
    "abbbbzhijoj",
    "abbbbzhijjj",
    ".abbbzyhiih",
    "..abbbzzy..",
]
HUNTER_MANTLE = [
    "..zWzzz......",
    ".zWzzyzzz....",
    "yzzyzyzyzy...",
    "qyyqyyqyyq...",
]
HUNTER_TORSO = [
    "...........",
    ".aabbbbbaa.",
    "abbccbbbaak",
    "abcbbbqbaak",
    "abbbbqbbaak",
    "abbbqbbbaak",
    "aabqbbbbaak",
    "kkkrkkkcckk",
    ".yqqyqqqqk.",
    ".yqyqqyqqk.",
]
HUNTER_LEG = [
    "kaa",
    "kab",
    "kab",
    "zWz",
    "abb",
    "abbb",
    "abbbb",
    "kaaaaa",
]


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


def hunter_cloak(c: Canvas, lx: int, ub: int, flutter: int = 0) -> None:
    for y in range(14 + ub, 26):
        k = y - 14 - ub
        x0 = round(10 + lx - k * 0.28 - (flutter if k > 5 else 0))
        for x in range(x0, 15 + lx):
            c.set(x, y, "y" if x == x0 and k < 6 else ("q" if x < x0 + 3 else "a"))
    hem_x0 = round(10 + lx - 11 * 0.28 - flutter)
    for i, x in enumerate(range(hem_x0, 15 + lx)):
        if i % 2 == 0:
            c.set(x, 26, "q" if i < 3 else "a")


def hunter(bob: int = 0, back_dx: int = 0, back_lift: int = 0, front_dx: int = 0, front_lift: int = 0,
           hand: tuple[float, float] = (21, 22), knife: float = 20, knife_shown: bool = True,
           back_hand: tuple[float, float] | None = None, lean: int = 0, crouch: int = 0, flutter: int = 0,
           blink: bool = False, fx: str | None = None) -> Canvas:
    c = Canvas(32, 32)
    ub = bob + crouch
    lx = lean
    # bow slung diagonally across the back
    for i in range(14):
        x = 7 + lx + round(i * 0.45 + 1.2 * math.sin(i / 13 * math.pi))
        y = 9 + ub + i
        c.set(x, y, "c" if i < 6 else "b")
    hunter_cloak(c, lx, ub, flutter)
    c.stamp(HUNTER_LEG, 12 + back_dx, 23 - back_lift, remap=DARKER)
    if back_hand:
        sleeve(c, 13 + lx, 16 + ub, back_hand[0] + lx, back_hand[1] + ub, "k", "a")
    c.stamp(HUNTER_TORSO, 10 + lx, 13 + ub)
    c.set(13 + lx, 20 + ub, "p")  # spare knife on the belt
    c.set(13 + lx, 21 + ub, "b")
    c.stamp(HUNTER_LEG, 16 + front_dx, 23 - front_lift)
    c.stamp(HUNTER_MANTLE, 9 + lx, 12 + ub)
    head = list(HUNTER_HEAD)
    if blink:
        head[6] = "abbbbzhijhj"
    c.stamp(head, 10 + lx, 2 + ub)
    hx, hy = hand[0] + lx, hand[1] + ub
    if knife_shown:
        draw_knife(c, hx, hy, knife)
    sleeve(c, 18 + lx, 15 + ub, hx, hy, "q", "y", cuff="a")
    if back_hand:
        c.set(back_hand[0] + lx, back_hand[1] + ub, "i")
    if fx == "throw":
        for (x, y, col) in ((26, 13, "W"), (28, 13, "z"), (29, 14, "W")):
            c.set(x, y, col)
    if fx in ("call", "call2"):
        for (x, y, col) in ((24, 8, "W"), (25, 9, "W"), (25, 10, "W"), (24, 11, "W"),
                            (27, 7, "z"), (28, 8, "z"), (28, 9, "z"), (28, 10, "z"), (27, 11, "z")):
            c.set(x, y + (1 if fx == "call2" else 0), col)
    if fx == "call2":
        for (x, y, col) in ((30, 7, "y"), (30, 11, "y"), (27, 2, "s")):
            c.set(x, y, col)
    return c


def hunter_sheet() -> Canvas:
    F = finish
    idle = [F(hunter(bob=b, blink=(i == 3))) for i, b in enumerate((0, 0, 1, 1))]
    walk = []
    for f in range(6):
        p = f / 6 * 2 * math.pi
        s = math.sin(p)
        fd = round(2.4 * s)
        fl = 1 if math.cos(p) > 0.5 else 0
        bl = 1 if math.cos(p) < -0.5 else 0
        bob = 0 if abs(s) > 0.6 else 1
        walk.append(F(hunter(bob=bob, front_dx=fd, back_dx=-fd, front_lift=fl, back_lift=bl,
                             hand=(21 - fd // 2, 22), knife=20 + fd * 6, flutter=1 if bob else 0)))
    attack = [
        F(hunter(hand=(18, 3), knife=-160, lean=-1, back_dx=-1, front_dx=1)),
        F(hunter(hand=(22, 3), knife=-90, back_dx=-1, front_dx=1)),
        F(hunter(hand=(25, 14), knife_shown=False, lean=1, back_dx=-2, front_dx=2, fx="throw")),
        F(hunter(hand=(23, 19), knife_shown=False, lean=1, back_dx=-2, front_dx=2)),
        F(hunter(hand=(21, 21), knife=20, back_dx=-1, front_dx=1)),
    ]
    hurt = [F(flash(hunter(lean=-1, hand=(20, 21)))), F(hunter(lean=-1, hand=(20, 21)))]
    pose = dict(hand=(20, 22), knife=60, lean=-1)
    death = fall_frames(hunter, pose, H_FOOT, 15, [-35, -70, -90, -90], 32, 32,
                        pre=[F(flash(hunter(lean=-1, hand=(20, 21)))), F(hunter(crouch=2, lean=-1, hand=(20, 21), knife=30))])
    cast = [
        F(hunter(hand=(21, 10), knife_shown=False)),
        F(hunter(hand=(21, 10), knife_shown=False, fx="call")),
        F(hunter(hand=(24, 4), knife_shown=False, bob=-1, back_dx=-1, front_dx=1, fx="call2")),
        F(hunter(hand=(23, 8), knife_shown=False, back_dx=-1, front_dx=1)),
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
                c.set(x, y, "vwxsW"[min(4, int(d * 5))])
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


def calm_patches(S: int, seed: int, base: str, shade: str) -> Canvas:
    """Two close tones in soft medium-size patches; no hard high-contrast blotches."""
    c = Canvas(S, S)
    n1 = periodic_noise(S, 8, seed)
    n2 = periodic_noise(S, 32, seed + 1)
    for y in range(S):
        for x in range(S):
            v = n1[y][x] * 0.75 + n2[y][x] * 0.25
            c.px[y][x] = shade if v < 0.45 else base
    return c


def grass_tile() -> Canvas:
    """Calm seamless grass: two close dark greens, sparse small tufts, one flower, one stone."""
    S = 64
    c = calm_patches(S, 11, "u", "G")
    rnd = random.Random(5)
    spots: list[tuple[int, int]] = []

    def free(x: int, y: int) -> bool:
        return all(min(abs(x - a), S - abs(x - a)) + min(abs(y - b), S - abs(y - b)) > 10 for a, b in spots)

    def pick() -> tuple[int, int]:
        for _ in range(200):
            x, y = rnd.randrange(S), rnd.randrange(S)
            if free(x, y):
                spots.append((x, y))
                return x, y
        return rnd.randrange(S), rnd.randrange(S)

    # tiny tufts: 3-4 px, one light blade + its own shadow
    for _ in range(9):
        x, y = pick()
        wrap_set(c, x, y, "v")
        wrap_set(c, x - 1, y + 1, "v")
        wrap_set(c, x + 1, y + 1, "v" if rnd.random() < 0.5 else "G")
        wrap_set(c, x, y + 1, "G")
    # single darker dimples for texture
    for _ in range(14):
        x, y = rnd.randrange(S), rnd.randrange(S)
        if c.px[y][x] == "u":
            wrap_set(c, x, y, "G")
    # one small flower, one pebble (sparse accents)
    x, y = pick()
    wrap_set(c, x, y, "s")
    wrap_set(c, x, y + 1, "G")
    x, y = pick()
    wrap_set(c, x, y, "n")
    wrap_set(c, x + 1, y, "m")
    wrap_set(c, x, y + 1, "t")
    wrap_set(c, x + 1, y + 1, "t")
    return c


def cave_tile() -> Canvas:
    """Calm seamless cave floor: two close greys, faint slab joints, a few pebbles."""
    S = 64
    c = calm_patches(S, 21, "m", "H")
    rnd = random.Random(9)
    seeds = [(rnd.uniform(0, S), rnd.uniform(0, S)) for _ in range(7)]
    for y in range(S):
        for x in range(S):
            ds = []
            for (sx, sy) in seeds:
                dx = min(abs(x + 0.5 - sx), S - abs(x + 0.5 - sx))
                dy = min(abs(y + 0.5 - sy), S - abs(y + 0.5 - sy))
                ds.append(math.sqrt(dx * dx + dy * dy))
            ds.sort()
            if ds[1] - ds[0] < 0.8:
                c.px[y][x] = "H"
    # a couple of short dark cracks
    for _ in range(3):
        x, y = rnd.randrange(S), rnd.randrange(S)
        for _ in range(rnd.randint(3, 5)):
            wrap_set(c, x, y, "D")
            x += rnd.choice((1, 1, 0))
            y += rnd.choice((1, 0, -1))
    # sparse pebbles
    for _ in range(4):
        x, y = rnd.randrange(S), rnd.randrange(S)
        wrap_set(c, x, y, "n")
        wrap_set(c, x, y + 1, "D")
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
# Decor (forest)
# ======================================================================================
def fir_tree() -> Canvas:
    c = Canvas(32, 48)
    c.rect(14, 38, 4, 8, "b")
    c.rect(14, 38, 1, 8, "c")
    c.rect(17, 38, 1, 8, "a")
    c.rect(12, 45, 8, 1, "a")
    c.set(12, 44, "b")
    c.set(19, 44, "a")
    tiers = [(41, 14), (32, 12), (24, 9), (16, 6)]
    for ti, (base, half) in enumerate(tiers):
        top = base - half - 5
        for y in range(top, base + 1):
            t = (y - top) / (base - top)
            w = half * t + 0.6
            for x in range(int(16 - w), int(16 + w) + 1):
                rel = (x + 0.5 - (16 - w)) / (2 * w)
                col = "w" if rel < 0.28 else ("v" if rel < 0.6 else "u")
                if ti > 0 or True:
                    if y - top < 2 and ti < 3:
                        pass
                c.set(x, y, col)
        # drooping branch tips along the lower edge
        for x in range(16 - half, 16 + half + 1, 3):
            c.set(x, base + 1, "v" if x < 16 else "u")
            c.set(x + 1, base + 1, "u" if x < 16 else "t")
        # shadow band the tier above casts on this tier
        if ti < len(tiers) - 1:
            nb, nh = tiers[ti + 1]
            for x in range(16 - nh, 16 + nh + 2):
                for dy in (2, 3):
                    if c.get(x, nb + dy) is not None:
                        c.set(x, nb + dy, "t" if x >= 16 else "u")
        c.set(16 - half + 3, base - 2, "x")
        c.set(16 - half // 2, base - half // 2 - 2, "x")
    c.set(16, 4, "x")
    c.set(15, 6, "x")
    return finish(c)


def bush() -> Canvas:
    c = Canvas(16, 16)
    for (x, y, r) in ((5, 10, 4), (11, 10, 4), (8, 7, 4.5)):
        c.shaded_ellipse(x, y, r, r * 0.85, "tuvwx")
    for x in range(2, 15):
        if c.get(x, 13) is not None:
            c.set(x, 13, "t")
    c.set(6, 9, "S")
    c.set(10, 7, "S")
    c.set(11, 11, "S")
    return finish(c)


def rock() -> Canvas:
    c = Canvas(16, 16)
    c.shaded_ellipse(8, 10, 6.5, 4.8, "Dmnp")
    c.shaded_ellipse(11.5, 12, 3.2, 2.6, "Dmn")
    c.line(7, 8, 9, 11, "D")
    c.set(5, 7, "w")
    c.set(6, 6, "v")
    c.set(7, 6, "w")
    return finish(c)


def stump() -> Canvas:
    c = Canvas(16, 16)
    c.rect(3, 7, 10, 6, "b")
    c.rect(3, 7, 2, 6, "c")
    c.rect(11, 7, 2, 6, "a")
    c.rect(1, 12, 3, 2, "b")
    c.rect(12, 12, 3, 2, "a")
    c.set(7, 10, "a")
    c.set(7, 11, "a")
    c.ellipse(8, 7, 5.2, 2.4, "d")
    c.ellipse(8, 7, 3.4, 1.5, "c")
    c.set(8, 7, "d")
    c.set(5, 6, "j")
    return finish(c)


# ======================================================================================
# Previews (scratch only)
# ======================================================================================
def upscale(rows: list[list[tuple]], k: int) -> list[list[tuple]]:
    out = []
    for row in rows:
        r = [p for p in row for _ in range(k)]
        for _ in range(k):
            out.append(list(r))
    return out


def compose(c: Canvas, bg: Canvas | None, solid: tuple | None) -> list[list[tuple]]:
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


def preview_pair(c: Canvas, grass: Canvas, k: int, path: Path, fw: int = 0, fh: int = 0) -> None:
    dark = (18, 16, 19, 255)
    a = upscale(compose(c, grass, None), k)
    b = upscale(compose(c, None, dark), k)
    # frame grid lines (faint) on dark copy
    if fw and fh:
        for y in range(len(b)):
            for x in range(len(b[0])):
                if (x % (fw * k) == 0 or y % (fh * k) == 0) and b[y][x] == dark:
                    b[y][x] = (40, 36, 44, 255)
    gap = [[(0, 0, 0, 255)] * len(a[0]) for _ in range(4)]
    write_png(a + gap + b, path)


def scene_preview(path: Path, grass: Canvas, sprites: dict[str, Canvas], decor: dict[str, Canvas]) -> None:
    W, H = 240, 160
    scene = Canvas(W, H)
    for y in range(H):
        for x in range(W):
            scene.px[y][x] = grass.px[y % 64][x % 64]

    def frame(sheet: Canvas, fw: int, fh: int, row: int = 0, col: int = 0) -> Canvas:
        f = Canvas(fw, fh)
        for y in range(fh):
            for x in range(fw):
                f.px[y][x] = sheet.px[row * fh + y][col * fw + x]
        return f

    def put(f: Canvas, x: int, y: int, mirror: bool = False) -> None:
        scene.blit(f.mirrored() if mirror else f, x, y)

    put(decor["fir"], 4, 2)
    put(decor["fir"], 200, 10)
    put(decor["fir"], 26, 110)
    put(decor["bush"], 60, 20)
    put(decor["rock"], 150, 130)
    put(decor["stump"], 110, 8)
    put(decor["bush"], 180, 120)
    put(frame(sprites["boss"], 64, 64, 0, 0), 150, 40, mirror=True)
    put(frame(sprites["warrior"], 32, 32, 1, 1), 90, 70)
    put(frame(sprites["warrior"], 32, 32, 2, 2), 50, 40)
    put(frame(sprites["goblin"], 24, 24, 1, 2), 130, 92, mirror=True)
    put(frame(sprites["goblin"], 24, 24, 0, 0), 140, 20, mirror=True)
    put(frame(sprites["wolf"], 24, 24, 1, 0), 60, 100)
    put(frame(sprites["skeleton"], 24, 24, 2, 1), 196, 96, mirror=True)
    put(frame(sprites["slime"], 24, 24, 0, 0), 100, 120)
    put(sprites["coin"], 84, 96)
    put(sprites["coin"], 78, 100)
    put(sprites["potion"], 124, 70)
    put(sprites["arrow"].mirrored(), 170, 104)
    put(sprites["bolt"], 128, 58)
    put(sprites["bolt"], 118, 52)
    put(sprites["slash"], 66, 40)
    one = compose(scene, None, None)
    two = upscale(one, 2)
    # 1x then 2x side by side, padded
    out = []
    for y in range(len(two)):
        left = one[y] if y < len(one) else [(0, 0, 0, 255)] * W
        out.append(left + [(0, 0, 0, 255)] * 6 + two[y])
    write_png(out, path)


def screen_preview(path: Path, ground: Canvas, sheets: dict[str, Canvas]) -> None:
    """360x640 phone screen at 1x next to its 180x320 centre at 2x."""
    W, H = 360, 640
    scene = Canvas(W, H)
    for y in range(H):
        for x in range(W):
            scene.px[y][x] = ground.px[y % 64][x % 64]

    def frame(sheet: Canvas, fs: int, row: int, col: int) -> Canvas:
        f = Canvas(fs, fs)
        for y in range(fs):
            for x in range(fs):
                f.px[y][x] = sheet.px[row * fs + y][col * fs + x]
        return f

    scene.blit(frame(sheets["warrior"], 32, 1, 1), 164, 300)
    for (k, x, y, row, col, mir) in (("goblin", 210, 290, 1, 2, True), ("goblin", 120, 330, 1, 4, False),
                                      ("wolf", 200, 340, 1, 1, True), ("wolf", 100, 270, 1, 3, False),
                                      ("skeleton", 230, 250, 0, 0, True), ("slime", 150, 360, 0, 1, False),
                                      ("goblin", 40, 100, 0, 0, False), ("wolf", 300, 520, 1, 0, True)):
        f = frame(sheets[k], 24, row, col)
        scene.blit(f.mirrored() if mir else f, x, y)
    scene.blit(frame(sheets["boss"], 64, 0, 0).mirrored(), 250, 120)
    one = compose(scene, None, None)
    crop = [row[90:270] for row in one[160:480]]
    two = upscale(crop, 2)
    out = [one[y] + [(0, 0, 0, 255)] * 8 + two[y] for y in range(H)]
    write_png(out, path)


def sheet_frame(sheet: Canvas, fw: int, fh: int, row: int, col: int) -> Canvas:
    f = Canvas(fw, fh)
    for y in range(fh):
        for x in range(fw):
            f.px[y][x] = sheet.px[row * fh + y][col * fw + x]
    return f


def heroes_previews(out_dir: Path, grass: Canvas, sheets: dict[str, Canvas], singles: dict[str, Canvas]) -> None:
    """heroes_closeup.png: idle/attack-hit/cast frames of the 5 heroes at 6x;
    heroes_ingame.png: 1x scene (5 heroes, companion wolf, enemies, projectiles) + the same at 3x."""
    order = ("warrior", "mage", "healer", "archer", "hunter")
    cols = [(0, 0), (1, 1), (2, 2), (5, 1), (4, 5)]
    close = Canvas(len(cols) * 34, len(order) * 33)
    for ri, k in enumerate(order):
        for ci, (row, col) in enumerate(cols):
            close.blit(sheet_frame(sheets[k], 32, 32, row, col), ci * 34, ri * 33)
    preview_pair(close, grass, 6, out_dir / "heroes_closeup.png")
    W, H = 200, 120
    scene = Canvas(W, H)
    for y in range(H):
        for x in range(W):
            scene.px[y][x] = grass.px[y % 64][x % 64]
    for i, k in enumerate(order):
        scene.blit(sheet_frame(sheets[k], 32, 32, 0, 0), 4 + i * 38, 6)
        scene.blit(sheet_frame(sheets[k], 32, 32, 1, 2), 4 + i * 38, 42)
    scene.blit(sheet_frame(sheets["wolf_companion"], 24, 24, 1, 1), 150, 88)
    scene.blit(sheet_frame(sheets["wolf_companion"], 24, 24, 0, 0), 112, 86)
    scene.blit(sheet_frame(sheets["wolf"], 24, 24, 1, 1).mirrored(), 176, 92)
    scene.blit(sheet_frame(sheets["goblin"], 24, 24, 0, 0).mirrored(), 66, 88)
    scene.blit(sheet_frame(sheets["skeleton"], 24, 24, 0, 0).mirrored(), 88, 82)
    scene.blit(sheet_frame(sheets["slime"], 24, 24, 0, 0), 40, 94)
    scene.blit(sheet_frame(sheets["wolf"], 24, 24, 0, 0), 4, 90)
    for i, k in enumerate(("arcane_bolt", "holy_bolt", "knife", "arrow")):
        scene.blit(singles[k], 138 + i * 10, 78)
    one = compose(scene, None, None)
    three = upscale(one, 3)
    gap = [[(0, 0, 0, 255)] * (W * 3) for _ in range(4)]
    write_png([r + [(0, 0, 0, 255)] * (W * 2) for r in one] + gap + three, out_dir / "heroes_ingame.png")
    vf = Canvas(64 * 3 + 8, 64)
    vf.blit(singles["nova"], 0, 0)
    vf.blit(singles["arcane_blast"], 68, 0)
    vf.blit(singles["heal_wave"], 136, 0)
    preview_pair(vf, grass, 3, out_dir / "hero_vfx.png")
    pr = Canvas(4 * 10, 8)
    for i, k in enumerate(("arcane_bolt", "holy_bolt", "knife", "arrow")):
        pr.blit(singles[k], i * 10, 0)
    preview_pair(pr, grass, 10, out_dir / "hero_projectiles.png")



# ======================================================================================
def main() -> None:
    preview_dir = None
    if "--preview" in sys.argv:
        preview_dir = Path(sys.argv[sys.argv.index("--preview") + 1])
        preview_dir.mkdir(parents=True, exist_ok=True)

    sheets = {
        "warrior": (warrior_sheet(), "sprites/characters/warrior.png", 32, 32),
        "goblin": (goblin_sheet(), "sprites/enemies/goblin.png", 24, 24),
        "wolf": (wolf_sheet(), "sprites/enemies/wolf.png", 24, 24),
        "skeleton": (skeleton_sheet(), "sprites/enemies/skeleton.png", 24, 24),
        "slime": (slime_sheet(), "sprites/enemies/slime.png", 24, 24),
        "boss": (guardian_sheet(), "sprites/enemies/forest_guardian.png", 64, 64),
        "mage": (mage_sheet(), "sprites/characters/mage.png", 32, 32),
        "healer": (healer_sheet(), "sprites/characters/healer.png", 32, 32),
        "archer": (archer_sheet(), "sprites/characters/archer.png", 32, 32),
        "hunter": (hunter_sheet(), "sprites/characters/hunter.png", 32, 32),
        "wolf_companion": (wolf_companion_sheet(), "sprites/companions/wolf_companion.png", 24, 24),
    }
    for _, (sh, rel, _, _) in sheets.items():
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
    for _, (cv, rel) in singles.items():
        save(cv, rel)
    icons = {"attack": icon_attack(), "skill": icon_skill(), "dash": icon_dash(), "bag": icon_bag(),
             "use": icon_use(), "pause": icon_pause()}
    for name, cv in icons.items():
        save(cv, f"ui/hud_icons/{name}.png")
    decor = {"fir": fir_tree(), "bush": bush(), "rock": rock(), "stump": stump()}
    for name, cv in decor.items():
        save(cv, f"sprites/decor/{ {'fir': 'fir_tree'}.get(name, name) }.png")

    gpl = ["GIMP Palette", "Name: Pixel Fantasy Survival master", "Columns: 8", "#"]
    for key, hx in PALETTE.items():
        gpl.append(f"{int(hx[0:2], 16):3d} {int(hx[2:4], 16):3d} {int(hx[4:6], 16):3d}\t{key} #{hx}")
    pal_path = REPO / "docs" / "art" / "source" / "master_palette.gpl"
    pal_path.parent.mkdir(parents=True, exist_ok=True)
    pal_path.write_text("\n".join(gpl) + "\n", encoding="utf-8")

    for rel, w, h in WRITTEN:
        print(f"  {rel}  {w}x{h}")
    print(f"  palette -> {pal_path.relative_to(REPO)}")

    if preview_dir:
        grass = singles["grass"][0]
        for name, (sh, _, fw, fh) in sheets.items():
            preview_pair(sh, grass, 4 if fw < 64 else 3, preview_dir / f"sheet_{name}.png", fw, fh)
        # small things sheet
        misc = Canvas(16 * 6 + 64 + 64 + 8, 64)
        x = 0
        for key in ("arrow", "bolt", "coin", "potion", "sword"):
            misc.blit(singles[key][0], x, 0)
            x += 18
        misc.blit(singles["slash"][0], x, 0)
        misc.blit(singles["nova"][0], x + 34, 0)
        preview_pair(misc, grass, 4, preview_dir / "misc.png")
        ic = Canvas(26 * 6, 24)
        for i, cv in enumerate(icons.values()):
            ic.blit(cv, i * 26, 0)
        hud_bg = Canvas(1, 1)
        hud_bg.px[0][0] = "S"
        preview_pair(ic, hud_bg, 5, preview_dir / "hud_icons.png")
        dc = Canvas(32 + 16 * 3 + 12, 48)
        dc.blit(decor["fir"], 0, 0)
        for i, k in enumerate(("bush", "rock", "stump")):
            dc.blit(decor[k], 34 + i * 18, 32)
        preview_pair(dc, grass, 5, preview_dir / "decor.png")
        tiles = Canvas(64 * 3, 64 * 2)
        for ty in range(2):
            for tx in range(3):
                tiles.blit(grass if ty == 0 else singles["cave"][0], tx * 64, ty * 64)
        write_png(upscale(to_rgba(tiles), 3), preview_dir / "tiles.png")
        for tname in ("grass", "cave"):
            screen_preview(preview_dir / f"screen_{tname}.png", singles[tname][0],
                           {k: v[0] for k, v in sheets.items()})
        sprites = {k: v[0] for k, v in sheets.items()}
        sprites.update({k: v[0] for k, v in singles.items()})
        scene_preview(preview_dir / "ingame.png", grass, sprites, decor)
        heroes_previews(preview_dir, grass, {k: v[0] for k, v in sheets.items()}, {k: v[0] for k, v in singles.items()})
        print(f"previews -> {preview_dir}")


if __name__ == "__main__":
    main()
