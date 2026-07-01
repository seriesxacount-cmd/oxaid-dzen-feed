# -*- coding: utf-8 -*-
"""Фабрика статей Оксайда на Gemini: ПИСАТЕЛЬ -> ПРОВЕРКА(редактор).
Ключ: env GEMINI_API_KEY (или .env рядом). Запуск: python article_factory.py "тема статьи"
Выводит: статью (title + HTML) и вердикт проверки (PASS/FAIL + замечания)."""
import os, sys, json, re, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
# ключ из окружения или .env (НЕ коммитить .env — он в .gitignore)
KEY = os.environ.get("GEMINI_API_KEY", "")
if not KEY and os.path.exists(os.path.join(HERE, ".env")):
    for line in open(os.path.join(HERE, ".env"), encoding="utf-8"):
        if line.strip().startswith("GEMINI_API_KEY"):
            KEY = line.split("=", 1)[1].strip()
MODEL = "gemini-2.5-flash"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={KEY}"

def gemini(prompt, temperature=0.7):
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": 8192}}
    req = urllib.request.Request(URL, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=90) as r:
        d = json.loads(r.read().decode("utf-8"))
    return d["candidates"][0]["content"]["parts"][0]["text"]

WRITER_PROMPT = """Ты — технический автор компании ООО «Оксайд» (Санкт-Петербург), производитель и поставщик промышленной химии (натр едкий, кислоты, коагулянты, консерванты).
Напиши экспертную B2B-статью для блога на тему: «{topic}».

Требования:
- Аудитория — закупщики и технологи промышленных предприятий (НЕ школьники, НЕ бытовые).
- Тон деловой, фактический. ЗАПРЕЩЕНЫ слова «премиум», «элитный», «инновационный», вода и штампы.
- Только проверяемые факты. Если не уверен в цифре/ГОСТе — пиши обобщённо, НЕ выдумывай номера ГОСТов, концентрации, классы опасности.
- Объём 2500–4000 знаков. Структура: вводный абзац, 3–5 подзаголовков (применение, марки/характеристики, хранение/перевозка, как выбрать/купить), в конце — короткий призыв обратиться в «Оксайд».
- Упомяни «Оксайд» естественно 1–2 раза (производитель/поставщик от 1 тонны, доставка по РФ, паспорт качества).
- ССЫЛКИ (обязательно, но только эти URL — другие НЕ выдумывай):
  • один раз в тексте дай ссылку на каталог: <a href="https://oxaid.ru/produkty">каталог продукции «Оксайд»</a>;
  • в конце — призыв со ссылкой на сайт и телефоном, например: «Свяжитесь с <a href="https://oxaid.ru/">ООО «Оксайд»</a> по телефону 8 (812) 320-40-09 — подберём марку и рассчитаем поставку.»

ПРАВИЛА ЖИВОГО ЯЗЫКА (чтобы текст НЕ звучал как нейросеть — соблюдай строго):
- Никакого антропоморфизма: рынок, цена, спрос, отрасль, день — не «дышат», не «решают», не «просыпаются», не «чувствуют». Пиши только конкретные действия людей и факты.
- Без «правила трёх»: не ставь три эпитета или три однородных пункта подряд ради ритма.
- Убери пафосные слова-«значимости»: «жест», «сдвиг», «манифест», «веха», «симфония», «ландшафт»/«экосистема» в переносном смысле, «драйвер», «вызов».
- Предлог «про» НЕ в значении «о»: пиши «статья о натре едком», «это влияет на качество» — НЕ «статья про натр», НЕ «это про качество».
- Минимум длинных тире (—); не злоупотребляй ими.
- Без штампов: «в современном мире», «играет важную роль», «не секрет, что», «широкий спектр», «на сегодняшний день», «неотъемлемая часть», «залог успеха».
- Конкретика вместо абстракций и воды. Короткие ясные предложения, живой деловой язык.

Верни СТРОГО в формате:
TITLE: <заголовок статьи, до 70 знаков, без кавычек>
---
<тело статьи в чистом HTML: <h2>, <p>, <ul><li>. Без <html>/<body>, без стилей.>"""

CHECKER_PROMPT = """Ты — строгий научный редактор ООО «Оксайд». Проверь статью на тему «{topic}».

Статья:
{article}

Проверь:
1. ФАКТЫ: нет ли выдуманных номеров ГОСТ, концентраций, классов опасности, дат, цифр. Помечай всё сомнительное.
2. БЕЗОПАСНОСТЬ: нет ли опасных/неверных рекомендаций по обращению с химией.
3. ТОН: нет ли слов «премиум/элитный/инновационный», воды, кликбейта.
4. ПОЛЬЗА: статья реально полезна закупщику, а не пустая.
5. ЖИВОЙ ЯЗЫК (анти-нейросеть): помечай антропоморфизм (рынок/цена/спрос «дышат», «решают»), «правило трёх» (три эпитета подряд), пафосные слова («жест», «сдвиг», «манифест», «веха», «драйвер»), предлог «про» вместо «о», штампы («в современном мире», «играет важную роль», «широкий спектр»), злоупотребление длинными тире.

Верни СТРОГО валидный JSON (без markdown-обёртки):
{{"verdict": "PASS" или "FAIL", "score": <0-100>, "issues": ["<проблема>", ...], "fixes": ["<что исправить>", ...]}}
Ставь FAIL, если есть выдуманные факты/ГОСТы, опасные советы, нарушен тон, или текст звучит как типичная нейросеть (антропоморфизм, «правило трёх», штампы, пафосные слова)."""

REWRITER_PROMPT = """Ты — технический автор ООО «Оксайд». Отредактируй свою статью на тему «{topic}», устранив ВСЕ замечания редактора. Сохрани структуру, ссылки, объём и живой язык; не добавляй новых ошибок.

Замечания редактора (обязательно исправить):
{fixes}

Текущая статья:
{article}

Верни СТРОГО в формате:
TITLE: <заголовок>
---
<исправленное тело статьи в чистом HTML>"""

def parse_article(text):
    m = re.search(r'TITLE:\s*(.+?)\s*\n-{3,}\s*\n(.+)', text, re.S)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return "(без заголовка)", text.strip()

def write_article(topic):
    return parse_article(gemini(WRITER_PROMPT.format(topic=topic), 0.7))

def check_article(topic, title, html):
    raw = gemini(CHECKER_PROMPT.format(topic=topic, article=title + "\n" + html), 0.2)
    raw = re.sub(r'^```json|```$', '', raw.strip(), flags=re.M).strip()
    try:
        return json.loads(raw)
    except Exception:
        return {"verdict": "FAIL", "score": 0, "issues": ["не распарсил ответ проверки"], "fixes": [raw[:300]]}

def rewrite_article(topic, title, html, fixes):
    ftxt = "\n".join("- " + f for f in fixes)
    return parse_article(gemini(REWRITER_PROMPT.format(topic=topic, fixes=ftxt, article=title + "\n" + html), 0.5))

def produce(topic, max_rewrites=1, log=lambda m: None):
    title, html = write_article(topic)
    v = check_article(topic, title, html)
    rounds = 0
    while v.get("verdict") != "PASS" and rounds < max_rewrites:
        log(f"  FAIL ({v.get('score')}) → переписываю по замечаниям...")
        title, html = rewrite_article(topic, title, html, v.get("fixes") or v.get("issues") or [])
        v = check_article(topic, title, html)
        rounds += 1
    return {"status": v.get("verdict"), "title": title, "html": html, "verdict": v, "rounds": rounds}

def main():
    if not KEY:
        print("НЕТ КЛЮЧА: GEMINI_API_KEY в .env или окружении."); return
    topic = sys.argv[1] if len(sys.argv) > 1 else "Натр едкий технический: марки, ГОСТ и как выбрать"
    print(f"=== ТЕМА: {topic} ===\nПишу + проверяю (с авто-переписью)...", flush=True)
    res = produce(topic, log=lambda m: print(m, flush=True))
    v = res["verdict"]
    vtxt = (f"Статус: {res['status']} | Оценка: {v.get('score')}/100 | переписей: {res['rounds']}\n"
            "Проблемы:\n" + "\n".join("  – " + i for i in v.get("issues", []) or ["нет"]) +
            "\nПравки:\n" + "\n".join("  – " + f for f in v.get("fixes", []) or ["нет"]))
    print("\n=== РЕЗУЛЬТАТ ===\n" + vtxt)
    print(f"\nЗАГОЛОВОК: {res['title']}\nДЛИНА: {len(re.sub('<[^>]+>','',res['html']))} знаков")
    save = r"C:\Users\shatalova.a\Desktop\Статья_тест.html"
    review = (f'<!doctype html><meta charset="utf-8"><body style="font-family:sans-serif;max-width:760px;margin:40px auto;line-height:1.6">'
              f'<div style="background:#0d203a;color:#fff;padding:16px 20px;border-radius:8px;margin-bottom:24px;white-space:pre-wrap">'
              f'<b>ПРОВЕРКА:</b>\n{vtxt}</div><h1>{res["title"]}</h1>{res["html"]}</body>')
    try:
        open(save, "w", encoding="utf-8").write(review); print("\nСохранено:", save)
    except Exception as e:
        print("не сохранил:", e)

if __name__ == "__main__":
    main()
