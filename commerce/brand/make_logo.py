"""Mlinjana Studios logo concepts, built as pure vector paths (no font files needed to display them).

Wordmark: Plus Jakarta Sans (SIL OFL 1.1, self-hosted in engine/static/fonts) converted to outlines. The dots of the
"i" and "j" are removed and redrawn in gold in the shape of each concept's symbol: the signature detail.
Usage: python3 brand/make_logo.py   → brand/logo/concepts/*.svg and brand/logo/board.html
"""
import io, math, os
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "..", "engine", "static", "fonts", "plusjakartasans.woff2")
OUT = os.path.join(HERE, "logo", "concepts")
GREEN, DEEP, GOLD, INK, MUTED = "#0b6b57", "#08503f", "#f5b301", "#0f172a", "#64748b"


def font_at(weight):
    f = TTFont(FONT)
    f = instantiateVariableFont(f, {"wght": weight})
    buf = io.BytesIO(); f.flavor = None; f.save(buf); buf.seek(0)
    return TTFont(buf)


F800, F700 = font_at(800), font_at(700)


def contours(font, ch):
    gs = font.getGlyphSet()
    name = font.getBestCmap()[ord(ch)]
    rec = DecomposingRecordingPen(gs)
    gs[name].draw(rec)
    out, cur = [], []
    for op, args in rec.value:
        if op == "moveTo" and cur:
            out.append(cur); cur = []
        cur.append((op, args))
    if cur:
        out.append(cur)
    return out, gs[name].width


def cbounds(c):
    pts = [p for _, args in c for p in args if p is not None]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def text_outline(font, text, size, x, y, tracking=0, strip_dots="ij"):
    """Returns (svg path d, width, [tittle (cx, cy, r)]) for text set at baseline y, left x, font size in px."""
    upm = font["head"].unitsPerEm
    s = size / upm
    xh = font["OS/2"].sxHeight
    d, tittles, pen_x = [], [], 0.0
    for ch in text:
        cs, adv = contours(font, ch)
        keep = []
        for c in cs:
            b = cbounds(c)
            if ch in strip_dots and b[1] > xh * 0.98:  # the dot sits wholly above the x-height
                tittles.append((x + (pen_x + (b[0] + b[2]) / 2) * s, y - (b[1] + b[3]) / 2 * s, (b[2] - b[0]) / 2 * s))
                continue
            keep.append(c)
        sp = SVGPathPen(None)
        tp = TransformPen(sp, (s, 0, 0, -s, x + pen_x * s, y))
        for c in keep:
            for op, args in c:
                getattr(tp, op)(*args)
        d.append(sp.getCommands())
        pen_x += adv + tracking
    return " ".join(d), (pen_x - tracking) * s, tittles


def tittle(shape, cx, cy, r, fill=GOLD):
    r *= 1.08
    if shape == "diamond":
        return f'<path d="M{cx:.2f} {cy - r * 1.25:.2f}L{cx + r * 1.25:.2f} {cy:.2f}L{cx:.2f} {cy + r * 1.25:.2f}L{cx - r * 1.25:.2f} {cy:.2f}Z" fill="{fill}"/>'
    if shape == "square":
        return f'<rect x="{cx - r:.2f}" y="{cy - r:.2f}" width="{2 * r:.2f}" height="{2 * r:.2f}" rx="{r * .32:.2f}" fill="{fill}"/>'
    if shape == "fold":  # a folded paper corner: right-angled triangle
        return f'<path d="M{cx - r:.2f} {cy - r:.2f}H{cx + r:.2f}V{cy + r:.2f}Z" fill="{fill}"/>'
    return f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="{fill}"/>'


# ---------- symbols (100 × 100) ----------
def reflect(p, a, b):
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    fx, fy = ax + t * dx, ay + t * dy
    return 2 * fx - px, 2 * fy - py


def sym_folio(dark=False):
    """Two pages side by side; their inner top corners are folded down, and the folds draw the M."""
    bg = f'<rect width="100" height="100" rx="24" fill="{GREEN}"/>'
    paper = "#ffffff"
    L = [(22, 78), (22, 22), (37, 22), (48.5, 47), (48.5, 78)]
    R = [(100 - x, y) for x, y in L][::-1]
    A, B = (37, 22), (48.5, 47)
    fl = reflect((48.5, 22), A, B)
    A2, B2 = (63, 22), (51.5, 47)
    fr = reflect((51.5, 22), A2, B2)
    poly = lambda pts: "M" + "L".join(f"{x:.2f} {y:.2f}" for x, y in pts) + "Z"
    return (bg + f'<path d="{poly(L)}" fill="{paper}"/><path d="{poly(R)}" fill="{paper}"/>' +
            f'<path d="{poly([A, B, fl])}" fill="{GOLD}"/><path d="{poly([A2, B2, fr])}" fill="{GOLD}"/>')


GRID = ["X...X", "XX.XX", "X.G.X", "X...X", "X...X"]


def sym_grid(dark=False):
    """An M drawn in the cells of a 5 × 5 planner grid; the centre cell, where the strokes meet, is gold."""
    cell, gap, m = 15.2, 4, 4
    out = []
    for r, row in enumerate(GRID):
        for c, v in enumerate(row):
            x, y = m + c * (cell + gap), m + r * (cell + gap)
            fill = {"X": "#ffffff" if dark else GREEN, "G": GOLD, ".": "rgba(255,255,255,.12)" if dark else "#dcefe7"}[v]
            out.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{cell}" height="{cell}" rx="3.6" fill="{fill}"/>')
    return "".join(out)


def sym_seal(dark=False):
    """A round studio seal: the M with a gold diamond, ringed by the name, the country and the year."""
    out = [f'<circle cx="50" cy="50" r="49" fill="{GREEN}"/>',
           f'<circle cx="50" cy="50" r="39" fill="none" stroke="{GOLD}" stroke-width="1.6"/>']
    out.append(arc_text("MLINJANA STUDIOS", 50, 50, 43.4, top=True, size=7.4, fill="#ffffff", tracking=60))
    out.append(arc_text("SOUTH AFRICA · 2026", 50, 50, 43.4, top=False, size=6.6, fill="#d1fae5", tracking=60))
    for ang in (180, 0):
        cx, cy = 50 + 43.5 * math.cos(math.radians(ang)), 50 + 43.5 * math.sin(math.radians(ang))
        out.append(tittle("diamond", cx, cy, 1.5))
    d, w, tit = text_outline(F800, "M", 44, 0, 0)
    out.append(f'<g transform="translate({50 - w / 2:.2f} 66)"><path d="{d}" fill="#ffffff"/></g>')
    out.append(tittle("diamond", 50, 25.5, 3.2))
    return "".join(out)


def arc_text(text, cx, cy, r, top=True, size=8, fill="#fff", tracking=120):
    """Glyph outlines placed one by one along a circle (readable from outside on top, from inside at the bottom)."""
    upm = F700["head"].unitsPerEm
    s = size / upm
    widths = [contours(F700, ch)[1] + tracking for ch in text]
    total = sum(widths) - tracking
    ang_total = total * s / r
    a = -math.pi / 2 - ang_total / 2 if top else math.pi / 2 + ang_total / 2
    out = []
    for ch, w in zip(text, widths):
        aw = (w - tracking) * s / r
        mid = a + (aw / 2 if top else -aw / 2)
        if ch != " ":
            cs, adv = contours(F700, ch)
            sp = SVGPathPen(None)
            for c in cs:
                for op, args in c:
                    getattr(sp, op)(*args)
            gx, gy = cx + r * math.cos(mid), cy + r * math.sin(mid)
            rot = math.degrees(mid) + (90 if top else -90)
            dy = size * .36 if top else size * .36
            out.append(f'<g transform="translate({gx:.2f} {gy:.2f}) rotate({rot:.2f}) translate({-adv * s / 2:.2f} {dy:.2f}) scale({s:.5f} {-s:.5f})">'
                       f'<path d="{sp.getCommands()}" fill="{fill}"/></g>')
        a += (w * s / r) * (1 if top else -1)
    return "".join(out)


SYMBOLS = {"folio": (sym_folio, "fold"), "grid": (sym_grid, "square"), "seal": (sym_seal, "diamond")}


def wordmark(shape, dark=False, x=0, y=0, size=64):
    ink, sub = ("#ffffff", "#a7b4c6") if dark else (INK, MUTED)
    d, w, tits = text_outline(F800, "Mlinjana", size, x, y + size * .74, tracking=-12)
    d2, w2, _ = text_outline(F700, "STUDIOS", size * .26, x + size * .03, y + size * 1.12, tracking=420, strip_dots="")
    svg = f'<path d="{d}" fill="{ink}"/>' + "".join(tittle(shape, cx, cy, r) for cx, cy, r in tits) + f'<path d="{d2}" fill="{sub}"/>'
    return svg, max(w, w2), size * 1.18


def lockup(key, dark=False):
    sym, shape = SYMBOLS[key]
    icon = sym(dark)
    wm, w, h = wordmark_lower(dark) if key == "lower" else wordmark(shape, dark, x=0, y=0, size=64)
    H = 100
    gap = 22
    total = H + gap + w
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total:.1f} {H}" role="img" aria-label="Mlinjana Studios">'
            f'<g>{icon}</g><g transform="translate({H + gap} {(H - h) / 2 + 2:.1f})">{wm}</g></svg>')


def icon_svg(key, dark=False):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" role="img" aria-label="Mlinjana Studios">{SYMBOLS[key][0](dark)}</svg>'


# ---------- round 2 (owner: "more realistic and professional") ----------
def glyph_path(font, ch, size, cx, baseline, fill="#ffffff"):
    d, w, _ = text_outline(font, ch, size, 0, 0, strip_dots="")
    return f'<g transform="translate({cx - w / 2:.2f} {baseline:.2f})"><path d="{d}" fill="{fill}"/></g>'


def sym_corner(dark=False):
    """A solid M on a page whose top-right corner is folded over in gold."""
    r, c = 22, 30
    page = (f"M{r} 0H{100 - c}L100 {c}V{100 - r}A{r} {r} 0 0 1 {100 - r} 100H{r}A{r} {r} 0 0 1 0 {100 - r}"
            f"V{r}A{r} {r} 0 0 1 {r} 0Z")
    flap = f"M{100 - c} 0V{c - 4}A4 4 0 0 0 {100 - c + 4} {c}H100Z"
    shadow = f"M{100 - c} {c}H100L{100 - c + 5} {c + 7}Z"
    tile, ink = ("#ffffff", GREEN) if dark else (GREEN, "#ffffff")
    return (f'<path d="{page}" fill="{tile}"/><path d="{shadow}" fill="{DEEP}" opacity="{.25 if dark else .55}"/><path d="{flap}" fill="{GOLD}"/>'
            + glyph_path(F800, "M", 64, 46, 76, ink))


def sym_layers(dark=False):
    """Three stacked pages; the front page carries the M and a gold folded corner."""
    def page(x, y, rot, fill):
        return f'<rect x="{x}" y="{y}" width="54" height="70" rx="10" fill="{fill}" transform="rotate({rot} {x + 27} {y + 35})"/>'
    tile, ink, p1, p2 = ("#ffffff", GREEN, "rgba(255,255,255,.35)", "rgba(255,255,255,.6)") if dark else (GREEN, "#ffffff", "#a7dccb", "#2f9a7e")
    front = (f'<path d="M20 15H52L64 27V75A10 10 0 0 1 54 85H20A10 10 0 0 1 10 75V25A10 10 0 0 1 20 15Z" fill="{tile}"/>'
             f'<path d="M52 15V23A4 4 0 0 0 56 27H64Z" fill="{GOLD}"/>')
    return (page(38, 8, 14, p1) + page(26, 12, 7, p2) + front + glyph_path(F800, "M", 38, 37, 63, ink))


def sym_lower_m(dark=False):
    """Wordmark-led brand: a lowercase m with its gold diamond, in a circle."""
    d, w, _ = text_outline(F800, "m", 66, 0, 0, strip_dots="")
    tile, ink = ("#ffffff", GREEN) if dark else (GREEN, "#ffffff")
    return (f'<circle cx="50" cy="50" r="50" fill="{tile}"/>'
            f'<g transform="translate({50 - w / 2:.2f} 70)"><path d="{d}" fill="{ink}"/></g>' + tittle("diamond", 74, 28, 5.2))


def sym_check(dark=False):
    """An M whose middle stroke is a gold tick: planners, lists and jobs done."""
    tile, ink = ("#ffffff", GREEN) if dark else (GREEN, "#ffffff")
    return (f'<rect width="100" height="100" rx="24" fill="{tile}"/>'
            f'<path d="M25 74V27" stroke="{ink}" stroke-width="12" stroke-linecap="round" fill="none"/>'
            f'<path d="M75 74V27" stroke="{ink}" stroke-width="12" stroke-linecap="round" fill="none"/>'
            f'<path d="M36 47L48 61L66 33" stroke="{GOLD}" stroke-width="12" stroke-linecap="round" stroke-linejoin="round" fill="none"/>')


SYMBOLS.update({"corner": (sym_corner, "square"), "layers": (sym_layers, "circle"),
                "lower": (sym_lower_m, "diamond"), "check": (sym_check, "square")})


def wordmark_lower(dark=False, x=0, y=0, size=64):
    ink, sub = ("#ffffff", "#cbd5e1") if dark else (GREEN, INK)
    d, w, tits = text_outline(F800, "mlinjana", size, x, y + size * .74, tracking=-14)
    d2, w2, _ = text_outline(F700, "STUDIOS", size * .2, 0, 0, tracking=380, strip_dots="")
    sx = x + w - w2
    return (f'<path d="{d}" fill="{ink}"/>' + "".join(tittle("diamond", cx, cy, r) for cx, cy, r in tits) +
            f'<g transform="translate({sx:.2f} {y + size * 1.1:.2f})"><path d="{d2}" fill="{sub}"/></g>'), w, size * 1.12


BOARD_CSS = """body{margin:0;font:15px/1.5 system-ui,Arial;background:#eef0f3;color:#0f172a;padding:28px}
h1{margin:0 0 4px;font-size:26px}.sub{margin:0 0 20px;color:#64748b}
section{background:#fff;border-radius:16px;padding:22px;margin-bottom:22px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.meta h2{margin:0;font-size:20px}.meta p{margin:4px 0 14px;color:#475569;max-width:900px}
.row{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px}
.cell{border-radius:12px;padding:26px;display:flex;align-items:center;gap:22px;min-height:120px}
.light{background:#fff;border:1px solid #e2e8f0}.dark{background:#0b1220}
.big svg{height:96px;width:auto;max-width:100%}
.i svg{display:block}.i96 svg{width:96px;height:96px}.i48 svg{width:48px;height:48px}.i32 svg{width:32px;height:32px}.i16 svg{width:16px;height:16px}
.sizes span{color:#64748b;font-size:13px;margin-left:auto}
.hdr{background:#f1f3f6;flex-direction:column;align-items:stretch;gap:10px;padding:16px}
.mockhdr{background:#fff;border-radius:10px;display:flex;align-items:center;gap:16px;padding:12px 16px}
.lk svg{height:40px;width:auto}.srch{flex:1;border:2px solid #0b6b57;border-radius:10px;padding:8px 12px;color:#94a3b8;font-size:13px}
.tab{display:flex;align-items:center;gap:8px;background:#dfe3e8;border-radius:8px 8px 0 0;padding:7px 12px;width:300px;font-size:12px;color:#334155}.fav svg{width:16px;height:16px;display:block}"""
CONCEPTS = {"folio": ("A · Folio", "Two pages whose folded corners draw the M: templates and printables. The i and j dots are little gold folds."),
            "grid": ("B · Planner grid", "The M is drawn in the cells of a planner grid, with a gold centre cell: spreadsheets, calendars and planners. The i and j dots are gold cells."),
            "seal": ("C · Studio seal", "A round maker's seal: name, country and founding year around a bold M. The i and j dots are gold diamonds.")}


def board():
    rows = []
    for k, (t, desc) in CONCEPTS.items():
        L, LD, I = lockup(k), lockup(k, True), icon_svg(k)
        rows.append(f'''<section><div class="meta"><h2>{t}</h2><p>{desc}</p></div>
<div class="row"><div class="cell light big">{L}</div><div class="cell dark big">{LD}</div></div>
<div class="row sizes"><div class="cell light"><div class="i i96">{I}</div><div class="i i48">{I}</div><div class="i i32">{I}</div><div class="i i16">{I}</div><span>app icon · 48 · 32 · 16 px</span></div>
<div class="cell hdr"><div class="mockhdr"><div class="lk">{L}</div><div class="srch">What are you looking for?</div></div><div class="tab"><div class="fav">{I}</div>Mlinjana Studios — Templates, planners…</div></div></div></section>''')
    open(os.path.join(HERE, "logo", "board.html"), "w").write(
        f'<!doctype html><meta charset="utf-8"><title>Logo concepts</title><style>{BOARD_CSS}</style><h1>Mlinjana Studios — logo concepts</h1>'
        '<p class="sub">Each concept: full logo on light and dark, the symbol at app-icon and browser-tab sizes, and in the site header. '
        'Brand colours stay the same (green #0b6b57, gold #f5b301).</p>' + "".join(rows))


def main():
    os.makedirs(OUT, exist_ok=True)
    for k in SYMBOLS:
        for dark in (False, True):
            sfx = "-dark" if dark else ""
            open(os.path.join(OUT, f"{k}-lockup{sfx}.svg"), "w").write(lockup(k, dark))
            open(os.path.join(OUT, f"{k}-icon{sfx}.svg"), "w").write(icon_svg(k, dark))
    board()
    print("wrote", len(os.listdir(OUT)), "files to", OUT, "and logo/board.html")


if __name__ == "__main__":
    main()


# ---------- brand board (round 2): palette + real-world mockups ----------
PALETTE = [  # name, hex, role
    ("Emerald", "#0b6b57", "Primary: logo, buttons, links"),
    ("Deep Emerald", "#08503f", "Hover states, dark panels"),
    ("Marigold", "#f5b301", "Accent: logo details, highlights. Never for text on white"),
    ("Ink", "#0f172a", "Headings and body text"),
    ("Slate", "#64748b", "Secondary text"),
    ("Mist", "#f1f3f6", "Page background"),
    ("Mint", "#e7f3ee", "Soft green tint for panels and badges"),
    ("Signal Red", "#d92d20", "Real discounts and errors only"),
]


def _lum(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


ROUND2 = {"corner": ("D · Folded page", "A bold M on a page with its corner folded over in gold. Simple and confident, like a well-known app icon; says 'documents and templates' at a glance."),
          "lower": ("E · Wordmark", "Like Takealot and Shein, the name is the logo: a lowercase mlinjana with gold diamond dots, and a matching 'm' badge for small spaces."),
          "check": ("F · Done", "The middle of the M is a gold tick: planners, checklists and jobs done. Friendly and memorable."),
          "layers": ("G · Stacked pages", "Three stacked pages with the M on top: a whole library of templates. A gold fold marks the front page.")}


def brand_board():
    sw = ""
    for name, hx, role in PALETTE:
        txt = "#ffffff" if contrast(hx, "#ffffff") >= contrast(hx, "#0f172a") else "#0f172a"
        cw, ci = contrast(hx, "#ffffff"), contrast(hx, "#0f172a")
        rgb = ", ".join(str(int(hx[i:i + 2], 16)) for i in (1, 3, 5))
        grade = lambda r: "AA" if r >= 4.5 else "large text only" if r >= 3 else "decoration only"
        pair = f"with white {cw:.1f}:1 ({grade(cw)})" if name != "Mist" and name != "Mint" else f"with Ink {ci:.1f}:1 ({grade(ci)})"
        sw += (f'<div class="sw"><div class="chip" style="background:{hx};color:{txt}"><b>{name}</b><span>{hx.upper()}</span></div>'
               f'<p>{role}</p><p class="mono">RGB {rgb} · {pair}</p></div>')
    secs = ""
    for k, (t, desc) in ROUND2.items():
        L, LD, I = lockup(k), lockup(k, True), icon_svg(k)
        apps = "".join(f'<div class="app"><div class="ai" style="background:{c}"></div><span>{n}</span></div>' for n, c in
                       [("Photos", "#f59e0b"), ("Maps", "#22c55e"), ("Mail", "#3b82f6"), ("Notes", "#eab308"),
                        ("Bank", "#7c3aed"), ("Music", "#ef4444"), ("Clock", "#111827")])
        secs += f'''<section><div class="meta"><h2>{t}</h2><p>{desc}</p></div>
<div class="g1"><div class="card-w">{L}</div><div class="card-g">{LD}</div></div>
<div class="g2">
  <div class="phone"><div class="screen"><div class="apps"><div class="app"><div class="ai mine">{I}</div><span>Mlinjana</span></div>{apps}</div></div></div>
  <div class="bcards"><div class="bc front">{LD}</div><div class="bc back"><div class="bi">{I}</div><div><b>Mlinjana Studios</b><span>Templates · Planners · Spreadsheets</span><span>mlinjanastudios.com</span></div></div></div>
  <div class="minis"><div class="tab"><div class="fav">{I}</div>Mlinjana Studios — Templates…<span>×</span></div>
    <div class="social"><div class="av">{I}</div><div><b>Mlinjana Studios</b><span>@mlinjanastudios · Digital downloads</span></div></div>
    <div class="sizes"><div class="s48">{I}</div><div class="s32">{I}</div><div class="s16">{I}</div><span>48 · 32 · 16 px</span></div></div>
</div></section>'''
    css = """*{box-sizing:border-box}body{margin:0;font:15px/1.5 system-ui,-apple-system,Segoe UI,Arial;background:#eef0f3;color:#0f172a;padding:30px}
h1{margin:0;font-size:28px}.sub{margin:4px 0 22px;color:#64748b}
section{background:#fff;border-radius:18px;padding:24px;margin-bottom:24px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.meta h2{margin:0;font-size:21px}.meta p{margin:4px 0 16px;color:#475569;max-width:880px}
.pal{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
.sw .chip{height:96px;border-radius:12px;padding:12px;display:flex;flex-direction:column;justify-content:flex-end;box-shadow:inset 0 0 0 1px rgba(0,0,0,.06)}
.sw .chip b{font-size:15px}.sw .chip span{font-size:12.5px;opacity:.85}.sw p{margin:6px 0 0;font-size:13px;color:#334155}.mono{font:12px ui-monospace,Menlo,monospace!important;color:#64748b!important}
.g1{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px}
.card-w,.card-g{border-radius:14px;padding:34px;display:flex;align-items:center;justify-content:center;min-height:150px}
.card-w{background:#fff;border:1px solid #e2e8f0}.card-g{background:#0b6b57}
.card-g svg path[fill="#a7b4c6"]{fill:#cdeee2}
.card-w svg,.card-g svg{height:92px;width:auto;max-width:100%}
.g2{display:grid;grid-template-columns:260px 1fr 330px;gap:16px;align-items:center}
.phone{width:240px;height:420px;border-radius:38px;background:#111;padding:10px;box-shadow:0 20px 40px -14px rgba(0,0,0,.45)}
.screen{height:100%;border-radius:30px;background:linear-gradient(160deg,#c7d2fe,#fbcfe8 55%,#fde68a);padding:40px 16px}
.apps{display:grid;grid-template-columns:repeat(4,1fr);gap:16px 10px}
.app{display:flex;flex-direction:column;align-items:center;gap:4px}.app span{font-size:9.5px;color:#111}
.ai{width:44px;height:44px;border-radius:11px}.ai.mine svg{width:44px;height:44px;display:block;border-radius:11px}
.bcards{position:relative;height:330px}
.bc{position:absolute;width:350px;height:200px;border-radius:12px;box-shadow:0 18px 36px -12px rgba(0,0,0,.35);display:flex;align-items:center;justify-content:center}
.bc.front{background:#0b6b57;left:0;top:0;transform:rotate(-4deg)}.bc.front svg{height:64px;width:auto}
.bc.back{background:#fff;left:230px;top:118px;transform:rotate(3deg);gap:16px;padding:20px;justify-content:flex-start}
.bc.back .bi svg{width:58px;height:58px;display:block}.bc.back b{display:block;font-size:16px}.bc.back span{display:block;font-size:12px;color:#475569}
.minis{display:grid;gap:14px}
.tab{display:flex;align-items:center;gap:8px;background:#e5e7eb;border-radius:9px 9px 0 0;padding:8px 12px;font-size:12.5px;color:#334155}.tab span{margin-left:auto;color:#94a3b8}.fav svg{width:16px;height:16px;display:block}
.social{display:flex;gap:12px;align-items:center;border:1px solid #e2e8f0;border-radius:12px;padding:12px}.av svg{width:56px;height:56px;display:block;border-radius:50%}
.social b{display:block}.social span{font-size:12.5px;color:#64748b}
.sizes{display:flex;gap:14px;align-items:center;border:1px solid #e2e8f0;border-radius:12px;padding:12px}.sizes span{margin-left:auto;font-size:12px;color:#64748b}
.s48 svg{width:48px;height:48px;display:block}.s32 svg{width:32px;height:32px;display:block}.s16 svg{width:16px;height:16px;display:block}"""
    open(os.path.join(HERE, "logo", "brand-board.html"), "w").write(
        f'<!doctype html><meta charset="utf-8"><title>Mlinjana Studios brand board</title><style>{css}</style>'
        '<h1>Mlinjana Studios — brand colours and logo options</h1><p class="sub">Round 2. Every logo is original vector artwork in the brand colours below, shown as it would appear in real use.</p>'
        f'<section><div class="meta"><h2>Brand colours</h2><p>One palette for the logo, the website, product images and print. Contrast ratios are calculated (WCAG: 4.5:1 or more is readable for normal text).</p></div><div class="pal">{sw}</div></section>'
        + secs)


# ---------- final assets (owner chose D · Folded page, 5 Nov 2026) ----------
FINAL = os.path.join(HERE, "logo", "final")


def export_final(key="corner"):
    """Vector masters; PNG/ICO sizes are rendered from these by render_png.js (Chromium)."""
    os.makedirs(FINAL, exist_ok=True)
    files = {"logo.svg": lockup(key), "logo-reversed.svg": lockup(key, True),
             "icon.svg": icon_svg(key), "icon-reversed.svg": icon_svg(key, True)}
    for name, svg in files.items():
        open(os.path.join(FINAL, name), "w").write(svg)
    # social sharing card (1200 × 630), rendered to og.png
    rev = lockup(key, True)
    open(os.path.join(FINAL, "og.html"), "w").write(
        '<!doctype html><meta charset="utf-8"><style>*{margin:0;box-sizing:border-box}body{width:1200px;height:630px;'
        'background:radial-gradient(900px 500px at 85% 0%,#118a6f,transparent 60%),#0b6b57;display:flex;flex-direction:column;'
        'justify-content:center;padding:0 110px;font-family:system-ui,Arial;color:#fff}svg{height:150px;width:auto}'
        'p{font-size:38px;font-weight:700;margin-top:46px;max-width:900px;line-height:1.25}span{display:block;margin-top:22px;'
        f'font-size:24px;color:#cdeee2;font-weight:600}}</style>{rev}<p>Printable planners, templates and spreadsheets, '
        'ready in minutes.</p><span>mlinjanastudios.com · Instant digital downloads</span>')
    return list(files) + ["og.html"]
