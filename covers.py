# -*- coding: utf-8 -*-
"""Отрисовка брендовой обложки Оксайда (общий модуль для фида и фабрики статей)."""
import os, re
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
FONT_DIR = os.path.join(ASSETS, "fonts")
MOL_T = os.path.join(ASSETS, "molecule_transparent.png")
MOL_W = os.path.join(ASSETS, "molecule_white.png")
W, H, PAD = 1536, 864, 96
TOP, BOTTOM, ACCENT = (13, 32, 58), (22, 63, 110), (60, 175, 220)

def font(sz, bold=True):
    fn = "PTSans-Bold.ttf" if bold else "PTSans-Regular.ttf"
    cands = [os.path.join(FONT_DIR, fn)]
    if bold:
        cands += [r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    else:
        cands += [r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for p in cands:
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()

def _grad():
    g = Image.new("RGB", (1, H))
    for y in range(H):
        t = y / H
        g.putpixel((0, y), tuple(int(TOP[i]*(1-t)+BOTTOM[i]*t) for i in range(3)))
    return g.resize((W, H)).convert("RGBA")

def _wrap(d, text, fnt, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur+" "+w).strip()
        if d.textlength(test, font=fnt) <= maxw:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def render_cover(title, out):
    img = _grad()
    src = MOL_T if os.path.exists(MOL_T) else MOL_W
    if os.path.exists(src):
        mol = Image.open(src).convert("RGBA")
        s = 900; mol = mol.resize((s, int(mol.height*s/mol.width)))
        mol.putalpha(mol.split()[3].point(lambda p: int(p*0.16)))
        img.alpha_composite(mol, (W-620, H-560))
    d = ImageDraw.Draw(img)
    fsz = 82
    while fsz > 44:
        fnt = font(fsz); lines = _wrap(d, title, fnt, W-2*PAD)
        if len(lines) <= 4: break
        fsz -= 6
    lh = int(fsz*1.22); y = (H-lh*len(lines))//2 - 50
    d.rectangle((PAD, y-46, PAD+120, y-34), fill=ACCENT)
    for ln in lines:
        d.text((PAD, y), ln, font=fnt, fill=(255, 255, 255)); y += lh
    mh = 104; ly = H-mh-66
    if os.path.exists(MOL_W):
        m = Image.open(MOL_W).convert("RGBA")
        mw = int(m.width*mh/m.height); m = m.resize((mw, mh))
        img.alpha_composite(m, (PAD, ly)); tx = PAD+mw+26
    else:
        tx = PAD
    d.text((tx, ly+8), "ОКСАЙД", font=font(60), fill=(255, 255, 255))
    d.text((tx+3, ly+70), "промышленная химия · СПб", font=font(28, bold=False), fill=(175, 205, 235))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.convert("RGB").save(out, "PNG")
