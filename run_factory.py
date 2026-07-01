# -*- coding: utf-8 -*-
"""Один прогон фабрики: берёт следующую тему -> пишет+проверяет (с переписью)
-> при PASS публикует статью (страница + обложка + запись в индекс для фида).
Состояние: state.json (published/held). Запуск: python run_factory.py"""
import os, re, json, html, datetime
import article_factory as af
from covers import render_cover

HERE = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(HERE, "public")
GEN = os.path.join(HERE, "generated")
SITE = "https://seriesxacount-cmd.github.io/oxaid-dzen-feed"

_TR = {'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'e','ж':'zh','з':'z','и':'i','й':'i',
       'к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f',
       'х':'h','ц':'ts','ч':'ch','ш':'sh','щ':'sch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya'}
def slugify(s):
    s = (s or "post").lower()
    s = "".join(_TR.get(c, c) for c in s)
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return (s[:60] or "post")

def load(p, default):
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else default
def save(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(obj, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

PAGE = """<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__ | Оксайд</title>
<meta name="description" content="__DESC__">
<style>
body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;color:#1a1a1a;margin:0;line-height:1.65}
.wrap{max-width:760px;margin:0 auto;padding:0 20px 60px}
.top{background:#0d203a;color:#fff;padding:14px 0}.top .wrap{padding:0 20px}
.cover{width:100%;border-radius:10px;margin:24px 0}
h1{font-size:32px;line-height:1.2;margin:24px 0 8px}
h2{font-size:22px;margin:28px 0 8px;color:#0d203a}
a{color:#1e6fb8}
.foot{margin-top:40px;padding-top:20px;border-top:1px solid #e2e2e2;color:#555;font-size:15px}
</style></head>
<body>
<div class="top"><div class="wrap"><b>ОКСАЙД</b> · промышленная химия · СПб</div></div>
<div class="wrap">
<img class="cover" src="../covers/gen/__SLUG__.png" alt="__TITLE__">
<h1>__TITLE__</h1>
__BODY__
<div class="foot">ООО «Оксайд» — производитель и поставщик промышленной химии, Санкт-Петербург.
Отгрузка от 1 тонны, доставка по России, паспорт качества на каждую партию.<br>
🌐 <a href="https://oxaid.ru/">oxaid.ru</a> · ☎ 8 (812) 320-40-09 · ✉ office@oxaid.ru</div>
</div></body></html>"""

def main():
    topics = load(os.path.join(HERE, "topics.json"), [])
    state = load(os.path.join(HERE, "state.json"), {"published": [], "held": []})
    done = set(state["published"]) | set(h["topic"] for h in state["held"])
    topic = next((t for t in topics if t not in done), None)
    if not topic:
        print("Новых тем нет — все обработаны."); return
    print("ТЕМА:", topic, flush=True)
    res = af.produce(topic, log=lambda m: print(m, flush=True))
    v = res["verdict"]
    slug = slugify(res["title"] or topic)
    if res["status"] == "PASS":
        render_cover(res["title"], os.path.join(PUBLIC, "covers", "gen", slug + ".png"))
        os.makedirs(GEN, exist_ok=True)
        open(os.path.join(GEN, slug + ".html"), "w", encoding="utf-8").write(res["html"])
        desc = re.sub(r'<[^>]+>', '', res["html"])[:160].replace('"', "'")
        page = (PAGE.replace("__TITLE__", html.escape(res["title"]))
                    .replace("__DESC__", html.escape(desc))
                    .replace("__SLUG__", slug).replace("__BODY__", res["html"]))
        os.makedirs(os.path.join(PUBLIC, "articles"), exist_ok=True)
        open(os.path.join(PUBLIC, "articles", slug + ".html"), "w", encoding="utf-8").write(page)
        idx = load(os.path.join(GEN, "index.json"), [])
        idx = [x for x in idx if x.get("slug") != slug]
        idx.insert(0, {"slug": slug, "title": res["title"],
                       "date": datetime.datetime.now(datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000"),
                       "cover": f"covers/gen/{slug}.png"})
        save(os.path.join(GEN, "index.json"), idx)
        state["published"].append(topic)
        print(f"✅ PASS ({v.get('score')}/100, переписей {res['rounds']}) → опубликовано: {slug}")
    else:
        state["held"].append({"topic": topic, "title": res["title"],
                              "score": v.get("score"), "issues": v.get("issues", []),
                              "date": datetime.datetime.now(datetime.timezone.utc).isoformat()})
        print(f"⚠️ FAIL после переписи ({v.get('score')}/100) → отложено на ручную проверку: {topic}")
    save(os.path.join(HERE, "state.json"), state)

if __name__ == "__main__":
    main()
