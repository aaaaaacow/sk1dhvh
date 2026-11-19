"""Any .ttf / .otf font -> a Lua block for renderer.load_font (own fonts in user Lua scripts).

Rasterizes the characters with FreeType (Pillow) at a pixel size, packs them into one white PNG atlas and prints:

    <NAME>_PNG = [[...Base64 PNG...]]
    <NAME>_GLYPHS = { [codepoint] = {x, y, w, h, offset_x, offset_y, advance}, ... }
    <NAME>_HEIGHT = <ascent + descent>

Paste the block into a script, then:

    local tex = renderer.load_png_base64(<NAME>_PNG)
    local font = renderer.load_font(tex, <NAME>_GLYPHS, {height = <NAME>_HEIGHT})
    -- in paint: renderer.font_text(font, x, y, 'hello', 255, 255, 255, 255)

Usage: python tools/lua_font_pack.py <font.ttf> <size px> <out.lua> [--name FONT] [--chars ascii,cyrillic] [--extra "€★"]
    [--merge <icons.ttf> <size px> <first-last hex range, e.g. f000-f2ff>]
Character sets: ascii (32-126), cyrillic (0400-045F), latin1 (00A0-00FF), or a hex range like 2190-21ff.
The atlas grows 256 -> 512 -> 1024 px wide as needed (renderer.load_png accepts up to 1024 x 1024, 1 MiB per script).
"""
import argparse
import base64
import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SETS = {'ascii': range(32, 127), 'cyrillic': range(0x400, 0x460), 'latin1': range(0xA0, 0x100)}
PAD = 1


def codes(spec):
    out = []
    for part in spec.split(','):
        part = part.strip().lower()
        if part in SETS:
            out += list(SETS[part])
        elif '-' in part:
            a, b = part.split('-')
            out += list(range(int(a, 16), int(b, 16) + 1))
        elif part:
            out.append(int(part, 16))
    return out


def raster(font, ch):
    """white glyph image (alpha = coverage), pen-relative offsets and advance; anchor la = left, ascender line"""
    l, t, r, b = font.getbbox(ch, anchor='la')
    advance = round(font.getlength(ch))
    if r <= l or b <= t:
        return None, 0, 0, advance
    mask = Image.new('L', (r - l, b - t), 0)
    ImageDraw.Draw(mask).text((-l, -t), ch, font=font, fill=255, anchor='la')
    if mask.getbbox() is None:
        return None, 0, 0, advance
    img = Image.new('RGBA', mask.size, (255, 255, 255, 0))
    img.putalpha(mask)
    return img, l, t, advance


def pack(images):
    for width in (256, 512, 1024):
        order = sorted(images, key=lambda k: -images[k].size[1])
        x = y = shelf = 0
        place = {}
        for k in order:
            w, h = images[k].size
            if x + w + PAD > width:
                x, y, shelf = 0, y + shelf + PAD, 0
            place[k] = (x, y)
            x += w + PAD
            shelf = max(shelf, h)
        if y + shelf <= 1024:
            return place, width, max(1, y + shelf)
    raise SystemExit('too many / too large glyphs for a 1024 x 1024 atlas: lower the size or the character set')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('font')
    ap.add_argument('size', type=int)
    ap.add_argument('out')
    ap.add_argument('--name', default='FONT')
    ap.add_argument('--chars', default='ascii,cyrillic')
    ap.add_argument('--extra', default='')
    ap.add_argument('--merge', nargs=3, metavar=('ICON_FONT', 'SIZE', 'RANGE'))
    a = ap.parse_args()

    font = ImageFont.truetype(a.font, a.size)
    ascent, descent = font.getmetrics()
    sources = [(font, c) for c in codes(a.chars) + [ord(c) for c in a.extra]]
    if a.merge:
        icon = ImageFont.truetype(a.merge[0], int(a.merge[1]))
        cmap = None
        try:
            from fontTools.ttLib import TTFont
            cmap = TTFont(a.merge[0]).getBestCmap()
        except ImportError:
            pass
        for c in codes(a.merge[2]):
            if cmap is None or c in cmap:
                sources.append((icon, c))

    images, glyphs = {}, {}
    for f, c in sources:
        img, ox, oy, adv = raster(f, chr(c))
        if f is not font:  # icons: center on the text line
            ia, idsc = f.getmetrics()
            oy += round((ascent + descent - (ia + idsc)) / 2)
        glyphs[c] = (ox, oy, adv)
        if img is not None:
            images[c] = img
    place, width, height = pack(images)
    sheet = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    for c, (x, y) in place.items():
        sheet.paste(images[c], (x, y))
    buf = io.BytesIO()
    sheet.save(buf, 'PNG', optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode()

    n = a.name
    out = ['-- %s %d px (tools/lua_font_pack.py): glyph = {x, y, w, h, offset_x, offset_y, advance}' % (Path(a.font).name, a.size),
           '%s_PNG = [[' % n]
    out += [b64[i:i + 120] for i in range(0, len(b64), 120)]
    out.append(']]')
    items = []
    for c in sorted(glyphs):
        ox, oy, adv = glyphs[c]
        x, y = place.get(c, (0, 0))
        w, h = images[c].size if c in images else (0, 0)
        items.append('[%d]={%d,%d,%d,%d,%d,%d,%d}' % (c, x, y, w, h, ox, oy, adv))
    out.append('%s_GLYPHS = {' % n)
    for i in range(0, len(items), 8):
        out.append('\t' + ','.join(items[i:i + 8]) + ',')
    out.append('}')
    out.append('%s_HEIGHT = %d' % (n, ascent + descent))
    Path(a.out).write_text('\n'.join(out) + '\n', encoding='utf-8')
    print('atlas %dx%d, %d glyphs, PNG %d bytes' % (width, height, len(glyphs), len(buf.getvalue())))


if __name__ == '__main__':
    main()
