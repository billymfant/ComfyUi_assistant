"""Assemble a 6-view orthographic modeling reference sheet ("blueprint").

Takes up to 6 named views (front/back/left/right/top/bottom) and lays them out in
the classic turnaround cross so a modeler can pin it as reference:

        [ TOP ]
  [LEFT][FRONT][RIGHT][BACK]
        [BOTTOM]

Draws light alignment guides (so proportions line up across views) + labels.
Any missing view is left blank. Pure PIL, no new deps.

Usage (module):
    from assemble_sheet import assemble
    assemble({"front":"f.png","right":"r.png",...}, "sheet.png", cell=768, title="Kiwano")
"""
import os
from PIL import Image, ImageDraw, ImageFont

# grid position (col,row) of each view in a 4-wide x 3-tall layout
SLOTS = {
    "top":    (1, 0),
    "left":   (0, 1),
    "front":  (1, 1),
    "right":  (2, 1),
    "back":   (3, 1),
    "bottom": (1, 2),
}
COLS, ROWS = 4, 3


def _font(size):
    for name in ("arial.ttf", "DejaVuSans.ttf", "seguisb.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _fit(img, cell, pad):
    """Fit an image into a square cell keeping aspect, on transparent bg."""
    box = cell - 2 * pad
    im = img.convert("RGBA")
    im.thumbnail((box, box), Image.LANCZOS)
    canvas = Image.new("RGBA", (cell, cell), (0, 0, 0, 0))
    canvas.alpha_composite(im, ((cell - im.width) // 2, (cell - im.height) // 2))
    return canvas


def assemble(views, out_path, cell=768, pad=24, title=None,
             bg=(247, 247, 249), guide=(210, 214, 222), label=(70, 74, 82)):
    W, H = COLS * cell, ROWS * cell + 60
    sheet = Image.new("RGBA", (W, H), bg + (255,))
    d = ImageDraw.Draw(sheet)
    y0 = 60  # header band

    # alignment guides: horizontal band around the middle row, vertical around front col
    fr_c, fr_r = SLOTS["front"]
    d.rectangle([0, y0 + fr_r * cell, W, y0 + (fr_r + 1) * cell], outline=guide, width=2)
    d.rectangle([fr_c * cell, y0, (fr_c + 1) * cell, H], outline=guide, width=2)

    lab = _font(26); ttl = _font(34)
    for name, (c, r) in SLOTS.items():
        x, y = c * cell, y0 + r * cell
        p = views.get(name)
        if p and os.path.exists(p):
            sheet.alpha_composite(_fit(Image.open(p), cell, pad), (x, y))
        # label chip
        d.rectangle([x + 8, y + 8, x + 8 + 92, y + 8 + 30], fill=(255, 255, 255, 230))
        d.text((x + 16, y + 12), name.upper(), fill=label, font=lab)

    if title:
        d.text((16, 12), title, fill=label, font=ttl)
    sheet.convert("RGB").save(out_path)
    return out_path


if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("views_json", help='JSON dict {"front":"path",...}')
    ap.add_argument("out")
    ap.add_argument("--cell", type=int, default=768)
    ap.add_argument("--title", default=None)
    a = ap.parse_args()
    v = json.loads(a.views_json)
    print("wrote", assemble(v, a.out, cell=a.cell, title=a.title))
