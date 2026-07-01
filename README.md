# oxaid-dzen-feed

Контент-завод: автоматически собирает **Дзен-совместимый RSS-фид** из блога [oxaid.ru](https://oxaid.ru/).

## Как работает
1. `gen_dzen_feed.py` читает Tilda-RSS блога, по каждой статье тянет полный текст (`<div itemprop="articleBody">`) и обложку, собирает фид с `content:encoded`, `guid`, `pubDate`, `enclosure`.
2. **GitHub Actions** (`.github/workflows/build.yml`) запускает генератор ежедневно (04:00 UTC) и при пуше.
3. **GitHub Pages** отдаёт готовый фид по постоянному URL.

## Фид
`https://<аккаунт>.github.io/oxaid-dzen-feed/feed.xml`

## Подключение к Дзену
Заявка на подключение RSS: https://yandex.ru/support/zen/website/rss-connect.html

_Публичный репозиторий — содержит только генератор и публичный фид, без секретов._
