"""Generate the animated architecture diagram used in the READMEs.

WHY THIS EXISTS
---------------
A static box-and-arrow diagram tells you what the components are. It does not
tell you what actually *happens* on a request. This script renders the same
components but animates a packet travelling the real request paths, so the
reader learns the data flow in a few seconds instead of reading prose.

WHY A GIF AND NOT AN ANIMATED SVG
---------------------------------
GitHub's markdown sanitiser neutralises SMIL/CSS animation inside SVG, so an
animated SVG renders as a still image in a README. GIF animates reliably.

WHY THIS SCRIPT IS COMMITTED
----------------------------
So the diagram is reproducible and editable. A binary GIF with no source is a
dead end the first time the architecture changes.

USAGE
-----
    pip install -r docs/architecture/requirements.txt
    python docs/architecture/generate_architecture_gif.py

Writes: docs/architecture/architecture.gif
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Canvas / palette
# ---------------------------------------------------------------------------
W, H = 900, 520
BG = (13, 17, 23)          # GitHub dark canvas — the diagram sits on dark READMEs
FG = (230, 237, 243)
MUTED = (125, 133, 144)
EDGE = (48, 54, 61)

CLIENT = (88, 166, 255)    # blue   — browser / frontend
API = (63, 185, 80)        # green  — FastAPI on Cloud Run
DATA = (210, 153, 34)      # amber  — Postgres
CACHE = (248, 81, 73)      # red    — Redis
EXTERNAL = (188, 140, 255) # purple — Gemini
PACKET = (255, 255, 255)

OUT = Path(__file__).with_name("architecture.gif")


def _font(size: int):
    """Prefer a real TTF; fall back to the bitmap default so this never crashes."""
    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
    ):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


F_TITLE = _font(21)
F_NODE = _font(14)
F_SUB = _font(11)
F_LABEL = _font(12)

# ---------------------------------------------------------------------------
# Nodes:  key -> (centre x, centre y, w, h, colour, title, subtitle)
# ---------------------------------------------------------------------------
NODES = {
    "browser": (110, 250, 150, 76, CLIENT, "Browser", "Next.js 15 · Vercel"),
    "api":     (395, 250, 172, 76, API, "FastAPI", "Cloud Run · us-central1"),
    "cache":   (395, 100, 150, 62, CACHE, "Redis", "cache · rate limit · pub/sub"),
    "db":      (700, 250, 150, 76, DATA, "PostgreSQL", "Neon · pooled"),
    # Deliberately off the api/cache vertical axis: the task -> cache (pub/sub)
    # edge would otherwise run straight through the FastAPI box and drop its
    # label on top of the node text.
    "task":    (170, 405, 150, 62, API, "Inline task", "moderation · email"),
    "llm":     (700, 100, 150, 62, EXTERNAL, "Gemini", "story generation"),
}

# Each scenario: (label, colour, [(from, to, hop-label), ...])
SCENARIOS = [
    (
        "1 · Cached read  >  GET /api/v1/stories/",
        CACHE,
        [
            ("browser", "api", "HTTP + gzip"),
            ("api", "cache", "cache hit"),
            ("cache", "api", "1.6 KB"),
            ("api", "browser", "0.62 s"),
        ],
    ),
    (
        "2 · Write + side effects  >  POST /api/v1/stories/",
        DATA,
        [
            ("browser", "api", "create"),
            ("api", "db", "async SQLAlchemy"),
            ("db", "api", "commit at seam"),
            ("api", "task", "moderate (inline)"),
            ("task", "cache", "pub/sub"),
            ("cache", "browser", "WebSocket push"),
        ],
    ),
    (
        "3 · AI streaming  >  POST /stories/generate/stream",
        EXTERNAL,
        [
            ("browser", "api", "prompt"),
            ("api", "llm", "generate"),
            ("llm", "api", "tokens"),
            ("api", "browser", "SSE · gzip skipped"),
        ],
    ),
]

FRAMES_PER_HOP = 7
HOLD_FRAMES = 5


def node_box(key):
    cx, cy, w, h, *_ = NODES[key]
    return cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2


def edge_point(key, toward):
    """Point on a node's border facing `toward` — so arrows touch edges, not centres."""
    cx, cy, w, h, *_ = NODES[key]
    tx, ty, *_ = NODES[toward]
    dx, dy = tx - cx, ty - cy
    if dx == 0 and dy == 0:
        return cx, cy
    # Scale the direction vector out to the box border.
    sx = (w / 2) / abs(dx) if dx else math.inf
    sy = (h / 2) / abs(dy) if dy else math.inf
    s = min(sx, sy)
    return cx + dx * s, cy + dy * s


def rounded(draw, box, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def centred(draw, text, cx, y, font, fill):
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    draw.text((cx - (right - left) / 2, y), text, font=font, fill=fill)


def draw_base(scenario_label, scenario_colour, active_edges):
    """Static layer: title, nodes, and every edge for the current scenario."""
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    centred(d, "Quill & Code  |  request flow", W // 2, 20, F_TITLE, FG)
    centred(d, scenario_label, W // 2, 50, F_LABEL, scenario_colour)

    # Edges first so boxes sit on top of the lines.
    for src, dst, label in active_edges:
        x1, y1 = edge_point(src, dst)
        x2, y2 = edge_point(dst, src)
        d.line([(x1, y1), (x2, y2)], fill=EDGE, width=2)

    for key, (cx, cy, w, h, colour, title, sub) in NODES.items():
        involved = any(key in (s, t) for s, t, _ in active_edges)
        box = node_box(key)
        rounded(d, box, 10, fill=(22, 27, 34), outline=colour if involved else EDGE,
                width=2 if involved else 1)
        centred(d, title, cx, cy - (18 if sub else 8), F_NODE, FG if involved else MUTED)
        if sub:
            centred(d, sub, cx, cy + 4, F_SUB, MUTED)

    # Legend
    d.text((24, H - 34), "animated: docs/architecture/generate_architecture_gif.py",
           font=F_SUB, fill=MUTED)
    return img


def build_frames():
    frames = []
    for label, colour, hops in SCENARIOS:
        for hop_index, (src, dst, hop_label) in enumerate(hops):
            x1, y1 = edge_point(src, dst)
            x2, y2 = edge_point(dst, src)
            for step in range(FRAMES_PER_HOP):
                t = step / (FRAMES_PER_HOP - 1)
                img = draw_base(label, colour, hops)
                d = ImageDraw.Draw(img)

                # Travelled portion of the path, drawn in the scenario colour.
                px, py = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
                d.line([(x1, y1), (px, py)], fill=colour, width=3)

                # Completed hops stay highlighted so the path accumulates.
                for done_src, done_dst, _ in hops[:hop_index]:
                    ax, ay = edge_point(done_src, done_dst)
                    bx, by = edge_point(done_dst, done_src)
                    d.line([(ax, ay), (bx, by)], fill=colour, width=3)

                # The packet, with a soft halo so it reads on a dark background.
                d.ellipse([px - 9, py - 9, px + 9, py + 9], fill=(colour[0] // 3,
                                                                  colour[1] // 3,
                                                                  colour[2] // 3))
                d.ellipse([px - 5, py - 5, px + 5, py + 5], fill=PACKET)

                # Hop caption offset PERPENDICULAR to the edge, so it never sits
                # on top of its own line (or on a node the line passes near).
                mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                ex, ey = x2 - x1, y2 - y1
                length = math.hypot(ex, ey) or 1.0
                nx, ny = -ey / length, ex / length          # unit normal
                if ny > 0:                                   # keep captions above the line
                    nx, ny = -nx, -ny
                centred(d, hop_label, mx + nx * 20, my + ny * 20 - 7, F_SUB, colour)
                frames.append(img)

        # Hold on the completed path so the eye can take it in.
        final = draw_base(label, colour, hops)
        fd = ImageDraw.Draw(final)
        for s, t_, _ in hops:
            ax, ay = edge_point(s, t_)
            bx, by = edge_point(t_, s)
            fd.line([(ax, ay), (bx, by)], fill=colour, width=3)
        frames.extend([final] * HOLD_FRAMES)
    return frames


def main():
    frames = build_frames()
    # Palette-quantise: flat-colour diagrams compress far better as 8-bit GIF.
    quantised = [f.quantize(colors=64, method=Image.MEDIANCUT) for f in frames]
    quantised[0].save(
        OUT,
        save_all=True,
        append_images=quantised[1:],
        duration=90,     # ms per frame
        loop=0,          # loop forever
        optimize=True,
        disposal=2,
    )
    size_kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT} — {len(frames)} frames, {size_kb:.0f} KB")
    if size_kb > 1500:
        print("WARNING: over the 1.5 MB README budget — reduce frames or canvas size")


if __name__ == "__main__":
    main()
