# -*- coding: utf-8 -*-
"""Генератор Дзен-совместимого RSS для блога Оксайда (Tilda /tpost/).
Берёт из Tilda-RSS список статей, тянет со страниц полный HTML статьи
(<div itemprop="articleBody">) + обложку, собирает фид с content:encoded/guid/enclosure."""
import re, time, sys, html, urllib.request, urllib.error
import xml.etree.ElementTree as ET

SRC_RSS = "https://oxaid.ru/rss-feed-259348515931.xml"
OUT = sys.argv[1] if len(sys.argv) > 1 else "feed.xml"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
MIN_LEN = 300

def fetch(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ru", "Referer": "https://oxaid.ru/"})
            return urllib.request.urlopen(req, timeout=45).read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (403, 429, 503) and i < tries - 1:
                time.sleep(3 * (i + 1)); continue
            raise

def article_html(h):
    m = re.search(r'<div[^>]*itemprop="articleBody"[^>]*>', h, re.I)
    if not m: return None
    start = m.end(); depth = 1
    for t in re.finditer(r'<(/?)div\b[^>]*>', h[start:], re.I):
        depth += 1 if t.group(1) == "" else -1
        if depth == 0:
            return h[start:start + t.start()]
    return None

def clean(frag):
    frag = re.sub(r'<(script|style|svg|noscript)\b.*?</\1>', ' ', frag, flags=re.S | re.I)
    # ленивые картинки Tilda: data-original -> src
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

def og_image(h):
    m = re.search(r'<meta property="og:image" content="([^"]+)"', h)
    return m.group(1) if m else None

def text_len(frag):
    return len(re.sub(r'<[^>]+>', '', frag or "").strip())

rss = fetch(SRC_RSS)
items = ET.fromstring(rss.encode()).find("channel").findall("item")
print(f"Статей в Tilda-RSS: {len(items)}", flush=True)

out_items, skipped = [], []
for it in items:
    title = (it.findtext("title") or "").strip()
    link = (it.findtext("link") or "").strip().replace("oxaid.tilda.ws", "oxaid.ru")
    pub = (it.findtext("pubDate") or "").strip()
    desc = (it.findtext("description") or "").strip()
    try:
        h = fetch(link)
    except Exception as e:
        skipped.append((title, f"загрузка: {e}")); continue
    raw = article_html(h)
    ce = clean(raw) if raw else ""
    tl = text_len(ce)
    if tl < MIN_LEN:
        skipped.append((title, f"текст {tl}<{MIN_LEN}")); continue
    out_items.append({"title": title, "link": link, "pub": pub, "desc": desc or title,
                      "img": og_image(h), "ce": ce, "tl": tl})
    print(f"  ✓ {title[:48]} ({tl} симв)", flush=True)
    time.sleep(1.2)

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
    if a["img"]: parts.append(f'<enclosure url="{esc(a["img"])}" type="image/jpeg" />')
    ce_safe = a['ce'].replace("]]>", "]]]]><![CDATA[>")
    parts += [f"<content:encoded><![CDATA[{ce_safe}]]></content:encoded>", "</item>"]
parts.append("</channel></rss>")
xml = "\n".join(parts)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(xml)

print(f"\n=== ИТОГ ===")
print(f"В фид: {len(out_items)} | размер: {len(xml.encode())} байт | {OUT}")
print(f"Пропущено (короткие/служебные): {len(skipped)}")
for t, why in skipped:
    print(f"   – {t[:45]} — {why}")
