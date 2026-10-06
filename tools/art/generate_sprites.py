#!/usr/bin/env python3
"""Pixel Fantasy Survival - procedural pixel-art generator (P0 art set).

Everything is drawn pixel by pixel at native resolution from one master
palette (32 colours) and written as PNG with zlib + struct (stdlib only).

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
}
assert len(PALETTE) == 34  # 32 sprite colours + 2 low-contrast ground tones
RGBA = {k: (int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16), 255) for k, v in PALETTE.items()}

# Ramps: one step darker / lighter inside the same material.
DARKER = {"d": "c", "c": "b", "b": "a", "a": "k", "k": "o", "g": "f", "f": "e", "e": "k",
          "j": "i", "i": "h", "h": "e", "p": "n", "n": "m", "m": "D", "D": "o", "s": "r", "r": "q",
          "q": "a", "x": "w", "w": "v", "v": "u", "u": "t", "t": "o", "G": "t", "H": "D", "z": "y", "y": "n", "W": "z",
          "S": "R", "R": "k", "C": "B", "B": "A", "A": "D", "o": "o"}
LIGHTER = {"o": "k", "k": "a", "a": "b", "b": "c", "c": "d", "d": "j", "e": "f", "f": "g", "g": "s",
           "h": "i", "i": "j", "j": "W", "D": "m", "m": "n", "n": "p", "p": "W", "q": "r", "r": "s",
           "s": "W", "t": "u", "G": "u", "H": "m", "u": "v", "v": "w", "w": "x", "x": "s", "y": "z", "z": "W", "W": "W",
           "R": "S", "S": "g", "A": "B", "B": "C", "C": "W"}

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
        print(f"previews -> {preview_dir}")


if __name__ == "__main__":
    main()
