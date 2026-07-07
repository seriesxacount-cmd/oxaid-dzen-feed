# -*- coding: utf-8 -*-
"""Генератор Дзен-совместимого RSS для блога Оксайда (Tilda /tpost/).
Тянет полный текст статьи из <div itemprop="articleBody"> + рисует брендовую обложку
(тёмно-синий фон + заголовок + молекула + логотип). Собирает фид с content:encoded/guid/enclosure.

Обложки: если covers/gen/<slug>.png уже есть (закоммичен) — используется он;
иначе рисуется на лету (для новых статей). Так текущие обложки = утверждённый вид."""
import re, os, time, sys, html, urllib.request, urllib.error
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
FONT_DIR = os.path.join(ASSETS, "fonts")
MOL_T = os.path.join(ASSETS, "molecule_transparent.png")
MOL_W = os.path.join(ASSETS, "molecule_white.png")

SRC_RSS = "https://oxaid.ru/rss-feed-259348515931.xml"
OUT = sys.argv[1] if len(sys.argv) > 1 else "feed.xml"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
MIN_LEN = 300
SITE = "https://seriesxacount-cmd.github.io/oxaid-dzen-feed"

# --- обложка ---
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

def cover_for(title, slug, outdir):
    rel = f"covers/gen/{slug}.png"
    dst = os.path.join(outdir, rel)
    if not os.path.exists(dst):
        render_cover(title, dst)
        print(f"    (отрисована обложка {slug})", flush=True)
    return f"{SITE}/{rel}"

# --- парсинг статей ---
def fetch(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ru", "Referer": "https://oxaid.ru/"})
            return urllib.request.urlopen(req, timeout=45).read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (403, 429, 503) and i < tries-1:
                time.sleep(3*(i+1)); continue
            raise

def article_html(h):
    m = re.search(r'<div[^>]*itemprop="articleBody"[^>]*>', h, re.I)
    if not m: return None
    start = m.end(); depth = 1
    for t in re.finditer(r'<(/?)div\b[^>]*>', h[start:], re.I):
        depth += 1 if t.group(1) == "" else -1
        if depth == 0:
            return h[start:start+t.start()]
    return None

def clean(frag):
    frag = re.sub(r'<(script|style|svg|noscript)\b.*?</\1>', ' ', frag, flags=re.S | re.I)
    frag = re.sub(r'<img[^>]*?\bdata-original="([^"]+)"[^>]*?>', r'<img src="\1" />', frag, flags=re.I)
    def strip_attrs(mt):
        tag = mt.group(1); attrs = mt.group(2) or ""
        if tag.lower() == "a":
            hm = re.search(r'\bhref="([^"]*)"', attrs)
            return f'<a href="{hm.group(1)}">' if hm else "<a>"
        if tag.lower() == "img":
            sm = re.search(r'\bsrc="([^"]*)"', attrs)
            return f'<img src="{sm.group(1)}" />' if sm else ""
        return f"<{tag}>"
    frag = re.sub(r'<([a-zA-Z0-9]+)((?:\s[^>]*)?)\s*/?>', strip_attrs, frag)
    frag = re.sub(r'[ \t]+', ' ', frag)
    frag = re.sub(r'(\s*\n\s*)+', '\n', frag)
    return frag.strip()

def text_len(frag):
    return len(re.sub(r'<[^>]+>', '', frag or "").strip())

# --- ЧИСТКА РЕКЛАМЫ под требования Дзена (телефон, email, CTA, ссылки на сайт) ---
_AD_MARK = re.compile(
    r'(обращайтесь|свяжитесь|закаж(ите|ем)|звоните|позвоните|оставьте?\s+заявку|'
    r'запрос\w*\s*цен|купить\s+у\s+нас|обратитесь\s+к\s+нам|заказать\s+у\s+нас|напишите\s+нам|'
    r'наш\s+менеджер|рассчита(ем|ю)|отгруж|наш\s+склад|поставщик\s+оксайд|'
    r'320[\s\-]?40[\s\-]?09|8[\s\-]?\(?812\)?|8[\s\-]?800|@oxaid\.ru|office@|@mail\.ru)', re.I)

def strip_ads(frag):
    if not frag:
        return frag
    # 1) снять ссылки на свой сайт (оставить текст)
    frag = re.sub(r'<a\b[^>]*(?:oxaid\.ru|tilda\.ws)[^>]*>(.*?)</a>', r'\1', frag, flags=re.I | re.S)
    # 2) удалить абзацы/пункты/подзаголовки с рекламными маркерами
    for tag in ('p', 'li', 'h2', 'h3'):
        frag = re.sub(rf'<{tag}\b[^>]*>.*?</{tag}>',
                      lambda m: '' if _AD_MARK.search(m.group(0)) else m.group(0),
                      frag, flags=re.I | re.S)
    # 2.5) остаточные CTA-фразы вне <p> (bare / в <div>) — режем от маркера до тега
    frag = re.sub(r'(?i)(оставьте?\s+заявку|обращайтесь|напишите\s+нам|'
                  r'запрос\w*\s*цен|рассчита\w+\s+цен|заказать\s+у\s+нас)[^<>]*', '', frag)
    # 3) добить оставшиеся телефон/почту в тексте
    frag = re.sub(r'8[\s\-]?\(?812\)?[\s\-]?320[\s\-]?40[\s\-]?09', '', frag)
    frag = re.sub(r'[a-zA-Z0-9._%+-]+@(?:oxaid\.ru|mail\.ru)', '', frag)
    frag = re.sub(r'<ul>\s*</ul>', '', frag, flags=re.I)
    frag = re.sub(r'[ \t]+', ' ', frag)
    return frag.strip()

# --- main ---
outdir = os.path.dirname(os.path.abspath(OUT)) or "."
rss = fetch(SRC_RSS)
items = ET.fromstring(rss.encode()).find("channel").findall("item")
print(f"Статей в Tilda-RSS: {len(items)}", flush=True)

out_items, skipped = [], []
for it in items:
    title = (it.findtext("title") or "").strip()
    link = (it.findtext("link") or "").strip().replace("oxaid.tilda.ws", "oxaid.ru")
    pub = (it.findtext("pubDate") or "").strip()
    desc = (it.findtext("description") or "").strip()
    slug = link.rstrip("/").split("/")[-1] or "post"
    try:
        h = fetch(link)
    except Exception as e:
        skipped.append((title, f"загрузка: {e}")); continue
    raw = article_html(h)
    ce = strip_ads(clean(raw)) if raw else ""
    tl = text_len(ce)
    if tl < MIN_LEN:
        skipped.append((title, f"текст {tl}<{MIN_LEN}")); continue
    img_url = cover_for(title, slug, outdir)
    out_items.append({"title": title, "link": link, "pub": pub, "desc": desc or title,
                      "img": img_url, "ce": ce, "tl": tl})
    print(f"  ✓ {title[:48]} ({tl} симв)", flush=True)
    time.sleep(1.0)

# --- авто-сгенерированные статьи (фабрика) ---
import json as _json
GENDIR = os.path.join(HERE, "generated")
gidx = os.path.join(GENDIR, "index.json")
if os.path.exists(gidx):
    gen = _json.load(open(gidx, encoding="utf-8"))
    added = 0
    for g in gen:
        bpath = os.path.join(GENDIR, g["slug"] + ".html")
        if not os.path.exists(bpath):
            continue
        body = strip_ads(open(bpath, encoding="utf-8").read())
        desc = re.sub(r'<[^>]+>', ' ', body)
        desc = re.sub(r'\s+', ' ', desc).strip()[:180]
        out_items.append({"title": g["title"],
                          "link": f"{SITE}/articles/{g['slug']}.html",
                          "pub": g.get("date", ""),
                          "desc": desc or g["title"],
                          "img": f"{SITE}/{g['cover']}",
                          "ce": body, "tl": len(desc)})
        added += 1
    print(f"Добавлено авто-статей из фабрики: {added}", flush=True)

def esc(s): return html.escape(s or "", quote=True)
parts = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">',
         '<channel>',
         '<title>Оксайд — промышленная химия</title>',
         '<link>https://oxaid.ru/</link>',
         '<description>Статьи о промышленной химии: натр едкий, кислоты, коагулянты, консерванты. Производитель и поставщик, Санкт-Петербург.</description>',
         '<language>ru</language>']
for a in out_items:
    parts += ["<item>",
              f"<title>{esc(a['title'])}</title>",
              f"<link>{esc(a['link'])}</link>",
              f'<guid isPermaLink="true">{esc(a["link"])}</guid>']
    if a["pub"]: parts.append(f"<pubDate>{esc(a['pub'])}</pubDate>")
    parts.append(f"<description>{esc(a['desc'])}</description>")
    parts.append(f'<enclosure url="{esc(a["img"])}" type="image/png" />')
    ce_safe = a['ce'].replace("]]>", "]]]]><![CDATA[>")
    parts += [f"<content:encoded><![CDATA[{ce_safe}]]></content:encoded>", "</item>"]
parts.append("</channel></rss>")
xml = "\n".join(parts)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(xml)

print(f"\n=== ИТОГ ===")
print(f"В фид: {len(out_items)} | размер: {len(xml.encode())} байт | {OUT}")
print(f"Пропущено: {len(skipped)}")
for t, why in skipped:
    print(f"   – {t[:45]} — {why}")
