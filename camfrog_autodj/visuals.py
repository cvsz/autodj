"""Pure helpers behind the GUI's look and animation (no tkinter import, so they are unit-tested headless)."""

from __future__ import annotations

import math


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def rgb_to_hex(r: float, g: float, b: float) -> str:
    c = lambda v: max(0, min(255, round(v)))
    return f"#{c(r):02x}{c(g):02x}{c(b):02x}"


def lerp_color(a: str, b: str, t: float) -> str:
    t = max(0.0, min(1.0, t))
    (r1, g1, b1), (r2, g2, b2) = hex_to_rgb(a), hex_to_rgb(b)
    return rgb_to_hex(r1 + (r2 - r1) * t, g1 + (g2 - g1) * t, b1 + (b2 - b1) * t)


def gradient(stops: list[str], n: int) -> list[str]:
    """n colours evenly spread over a multi-stop gradient."""
    if n <= 1:
        return [stops[0]] * max(n, 0)
    out = []
    for i in range(n):
        x = i / (n - 1) * (len(stops) - 1)
        k = min(int(x), len(stops) - 2)
        out.append(lerp_color(stops[k], stops[k + 1], x - k))
    return out


def bar_heights(t: float, n: int, level: float) -> list[float]:
    """Target heights 0..1 for an n-bar equaliser at time t. level: 1 = playing, small = paused/idle.
    Decorative: a blend of travelling sines (it is not an analysis of the audio)."""
    level = max(0.0, min(1.0, level))
    out = []
    for i in range(n):
        x = i / max(n - 1, 1)
        v = (
            (0.5 + 0.5 * math.sin(t * 3.1 + i * 0.62)) * 0.55
            + (0.5 + 0.5 * math.sin(t * 5.3 - i * 1.17 + 1.3)) * 0.30
            + (0.5 + 0.5 * math.sin(t * 1.7 + x * 6.0)) * 0.15
        )
        shape = 0.55 + 0.45 * math.sin(
            math.pi * (0.12 + 0.76 * x)
        )  # a little lower at both edges
        out.append(max(0.03, min(1.0, v * shape * level + 0.03)))
    return out


def ease(cur: float, target: float, up: float = 0.55, down: float = 0.14) -> float:
    """Move cur toward target: quick attack, slow decay (looks like a real meter)."""
    return cur + (target - cur) * (up if target > cur else down)


def vinyl_angle(t: float, rpm: float = 33.3) -> float:
    return (t * rpm * 6.0) % 360.0  # rpm * 360 deg / 60 s


def pulse(t: float, period: float = 1.6) -> float:
    """0..1 smooth pulse (used for the ON AIR light and glow)."""
    return 0.5 - 0.5 * math.cos(2 * math.pi * t / period)


def aurora_offset(t: float, i: int, n: int) -> float:
    """0..1 vertical wobble for aurora band i of n, at time t (for a slow drifting gradient backdrop)."""
    return 0.5 + 0.5 * math.sin(t * (0.09 + 0.025 * i) + i * 1.7)


def make_particles(n: int, seed: int = 0) -> list[dict]:
    """n floating sparkle particles with a fixed per-particle phase/speed/radius/orbit, seeded for stability."""
    rnd = []
    x = (seed * 9301 + 49297) % 233280
    for i in range(n):
        x = (x * 9301 + 49297) % 233280
        rnd.append(x / 233280)
    out = []
    for i in range(n):
        r0, r1, r2, r3 = (
            rnd[(i * 4) % n],
            rnd[(i * 4 + 1) % n],
            rnd[(i * 4 + 2) % n],
            rnd[(i * 4 + 3) % n],
        )
        out.append(
            {
                "phase": r0 * 6.283,
                "speed": 0.15 + r1 * 0.35,
                "orbit": 0.55 + r2 * 0.9,
                "size": 1.5 + r3 * 2.5,
                "tilt": r0 * 6.283,
            }
        )
    return out


def particle_pos(
    p: dict, t: float, cx: float, cy: float, base_r: float
) -> tuple[float, float, float]:
    """x, y, alpha(0..1) for one particle at time t, drifting in a loose ellipse around (cx, cy)."""
    a = p["phase"] + t * p["speed"]
    rx = base_r * p["orbit"]
    ry = rx * 0.55
    ct, st = math.cos(p["tilt"]), math.sin(p["tilt"])
    ex, ey = rx * math.cos(a), ry * math.sin(a)
    x = cx + ex * ct - ey * st
    y = cy + ex * st + ey * ct
    alpha = 0.35 + 0.65 * pulse(t * p["speed"] * 1.3 + p["phase"], 1.0)
    return x, y, alpha


def confetti_burst(n: int, seed: int = 0) -> list[dict]:
    """n confetti pieces launched outward from the centre (fixed initial velocity/angle/spin), t=0 at launch."""
    rnd = []
    x = (seed * 9301 + 49297) % 233280
    for i in range(n * 3):
        x = (x * 9301 + 49297) % 233280
        rnd.append(x / 233280)
    out = []
    for i in range(n):
        ang = rnd[i * 3] * 6.283
        speed = 60 + rnd[i * 3 + 1] * 140
        out.append(
            {
                "angle": ang,
                "speed": speed,
                "spin": (rnd[i * 3 + 2] - 0.5) * 10,
                "size": 3 + rnd[i * 3] * 4,
            }
        )
    return out


def confetti_pos(
    c: dict, age: float, cx: float, cy: float
) -> tuple[float, float, float, float]:
    """x, y, rotation(deg), alpha(0..1) for one confetti piece `age` seconds after launch. Lasts ~1.4s."""
    life = 1.4
    k = min(age / life, 1.0)
    vx, vy = (
        math.cos(c["angle"]) * c["speed"],
        math.sin(c["angle"]) * c["speed"] - 40,
    )  # slight upward bias
    x = cx + vx * age
    y = cy + vy * age + 0.5 * 220 * age * age  # gravity
    rot = c["spin"] * age * 60
    alpha = max(0.0, 1.0 - k)
    return x, y, rot, alpha


def round_rect_points(
    x1: float, y1: float, x2: float, y2: float, r: float
) -> list[float]:
    """Polygon points for a rounded rectangle; draw with smooth=True."""
    r = max(0.0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    return [
        x1 + r,
        y1,
        x1 + r,
        y1,
        x2 - r,
        y1,
        x2 - r,
        y1,
        x2,
        y1,
        x2,
        y1 + r,
        x2,
        y1 + r,
        x2,
        y2 - r,
        x2,
        y2 - r,
        x2,
        y2,
        x2 - r,
        y2,
        x2 - r,
        y2,
        x1 + r,
        y2,
        x1 + r,
        y2,
        x1,
        y2,
        x1,
        y2 - r,
        x1,
        y2 - r,
        x1,
        y1 + r,
        x1,
        y1 + r,
        x1,
        y1,
    ]
