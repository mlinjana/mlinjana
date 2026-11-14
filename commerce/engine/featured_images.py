"""Featured product pictures (owner, 14 Nov 2026: "standardise the featured products' images and cards").

One consistent 4:3 picture per featured product: the most telling real page of the product (a filled worked example,
a dashboard or summary), trimmed of empty margins and shown as a sheet on the shop's warm ivory background. Bundles
show three of their member products' sheets fanned. Nothing is invented: every pixel of content comes from the product's
own preview images or its PDF. Output: engine/static/brand/featured/<ID>.webp (copied to /assets/brand/featured/).
Usage: python3 engine/featured_images.py
"""
import glob, json, os, subprocess, tempfile
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "engine", "static", "brand", "featured")
W, H = 960, 720
# product -> source: ("preview", n) uses site/assets/p/<ID>/preview-n.webp; ("pdf", page) renders that page of its A4 PDF
SOURCES = {
    "ABL-009": ("preview", 1), "BZW-003": ("preview", 1), "ABL-025": ("preview", 2), "CHK-011": ("pdf", 3),
    "BZW-001": ("preview", 1), "FLW-023": ("preview", 1),
    "ABL-010": ("preview", 1), "ABL-011": ("preview", 1), "BZW-004": ("preview", 1), "BZW-005": ("preview", 1),
    "GLD-001": ("preview", 1), "GLD-002": ("preview", 1), "GLD-014": ("preview", 1),
}
BUNDLES = {"BZW-020": ["BZW-003", "BZW-004", "BZW-005"], "ABL-020": ["ABL-009", "ABL-010", "ABL-011"], "GLD-028": ["GLD-001", "GLD-002", "GLD-014"]}
FEATURED = ["ABL-009", "BZW-003", "ABL-025", "CHK-011", "BZW-001", "FLW-023", "BZW-020", "ABL-020", "GLD-028"]


def source(pid):
    kind, n = SOURCES.get(pid, ("preview", 1))
    if kind == "pdf":
        pdf = [f for f in glob.glob(os.path.join(ROOT, "build", "products", pid, "files", "*.pdf")) if "Letter" not in f][0]
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(["pdftoppm", "-r", "110", "-f", str(n), "-l", str(n), "-png", pdf, os.path.join(d, "p")], check=True)
            return Image.open(glob.glob(os.path.join(d, "p*.png"))[0]).convert("RGB")
    return Image.open(os.path.join(ROOT, "site", "assets", "p", pid, f"preview-{n}.webp")).convert("RGB")


def trim(im):
    """Cut the grey/white margin around the page so every sheet fills its frame the same way."""
    bg = Image.new("RGB", im.size, im.getpixel((2, 2)))
    box = ImageChops.difference(im, bg).convert("L").point(lambda v: 255 if v > 18 else 0).getbbox()
    return im.crop(box) if box else im


def sheet(im, width, height):
    """The page on a white card with rounded corners, filling a fixed frame: wide sheets are cropped from the left
    (where the headings and first columns are) but keep at least 92% of their width so charts stay whole; tall pages are cropped from the top."""
    im = trim(im)
    pad = int(width * 0.035)
    iw, ih = width - 2 * pad, height - 2 * pad
    aspect = iw / ih
    if im.width / im.height > aspect:
        cw = max(int(im.height * aspect), int(im.width * 0.92))
        im = im.crop((0, 0, cw, im.height))
    scale = iw / im.width
    im = im.resize((iw, max(1, int(im.height * scale))), Image.LANCZOS)
    card = Image.new("RGB", (width, height), "white")
    y0 = pad + max(0, (ih - im.height) // 2)
    card.paste(im.crop((0, 0, iw, min(ih, im.height))), (pad, y0))
    if im.height > ih:  # fade the cut edge so it reads as "more below", not a broken image
        fade = Image.linear_gradient("L").resize((width, int(height * 0.2)))
        card.paste(Image.new("RGB", fade.size, "white"), (0, height - fade.height), fade)
    mask = Image.new("L", card.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, width - 1, height - 1), radius=int(width * 0.025), fill=255)
    return card, mask


def canvas():
    c = Image.linear_gradient("L").resize((W, H)).point(lambda v: 255 - v // 14)
    base = Image.new("RGB", (W, H), (246, 241, 232))
    return Image.composite(base, Image.new("RGB", (W, H), (236, 229, 216)), c)


def drop(c, card, mask, x, y, angle=0):
    layer = Image.new("RGBA", c.size, (0, 0, 0, 0))
    rgba = card.convert("RGBA"); rgba.putalpha(mask)
    if angle:
        rgba = rgba.rotate(angle, resample=Image.BICUBIC, expand=True)
    shadow = Image.new("RGBA", rgba.size, (23, 36, 59, 0))
    shadow.putalpha(rgba.split()[3].point(lambda v: int(v * 0.28)))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    layer.alpha_composite(shadow, (x + 6, y + 16))
    layer.alpha_composite(rgba, (x, y))
    c.paste(Image.alpha_composite(c.convert("RGBA"), layer).convert("RGB"))


def single(pid):
    c = canvas()
    card, mask = sheet(source(pid), int(W * 0.84), int(H * 0.80))
    drop(c, card, mask, (W - card.width) // 2, int(H * 0.08))
    return c


def bundle(pid):
    """Three member products: two behind at the sides, one in front, all the same size."""
    c = canvas()
    back1, back2, front = BUNDLES[pid]
    cw, ch = int(W * 0.56), int(H * 0.62)
    for m, x, y, ang in ((back1, int(W * 0.05), int(H * 0.10), 5), (back2, int(W * 0.40), int(H * 0.08), -5)):
        card, mask = sheet(source(m), cw, ch)
        drop(c, card, mask, x, y, ang)
    card, mask = sheet(source(front), int(W * 0.62), int(H * 0.66))
    drop(c, card, mask, (W - card.width) // 2, int(H * 0.27))
    return c


def main():
    os.makedirs(OUT, exist_ok=True)
    for pid in FEATURED:
        im = bundle(pid) if pid in BUNDLES else single(pid)
        im.save(os.path.join(OUT, f"{pid}.webp"), quality=86)
        print(pid, os.path.getsize(os.path.join(OUT, f"{pid}.webp")) // 1024, "KB")


if __name__ == "__main__":
    main()
