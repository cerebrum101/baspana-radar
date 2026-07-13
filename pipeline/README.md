# Pipeline — T2

## Порядок действий

**0. Supabase (браузер, один раз).** supabase.com → New project (free) →
SQL Editor → вставить содержимое `schema.sql` → Run. Сохранить из
Settings → API: Project URL, `anon` key, `service_role` key.

**1. Зависимости (терминал, один раз):**
```bash
pip install httpx selectolax pandas supabase
```

**2. Проверка парсеров на 2 страницах (ОБЯЗАТЕЛЬНО перед полным прогоном):**
```bash
cd pipeline
python scrape_complexes.py --sample
python scrape_listings.py --sample
```
В диагностике заполненность ключевых полей (price, area, complex_slug)
должна быть ≥90%. Если нет — не запускайте полный прогон, пришлите мне
один файл из `raw/`, я починю парсер за пару минут.

**3. Полный прогон (домашняя сеть, не университетская):**
```bash
python scrape_complexes.py     # ~30-60 мин
python scrape_listings.py      # ~1.5-3 ч, можно Ctrl-C и перезапускать
```
Оба скрипта чекпоинтятся: перезапуск продолжает с места остановки.
Весь сырой HTML остаётся в `raw/` — перепарсить можно без сети.

**4. После скрейпа — офлайн-цепочка:**
```bash
python normalize.py            # чистка, PII, дедуп, привязка ЖК
python stats.py                # медианы, перцентили, аномалии
python train_valuation.py      # hedonic-модель (pip install scikit-learn)
python events_score.py         # инфраструктурный аплифт (events.json)
python load_supabase.py        # → Supabase
python generate_cards.py --limit 5   # Layer-1 карточки (ключ Gemini/Groq в .env)
python generate_cards_l2.py    # Layer-2 (сначала собрать sources/, см. README там)
python load_supabase.py --cards
python eval_cards.py           # метрика галлюцинаций → eval_report.md
```

## Что НЕ делает скрейпер
- не заходит на страницы объявлений (всё берётся из карточек выдачи);
- не сохраняет имена и телефоны продавцов — только тип (хозяин/агент);
- не обходит блокировки: при 5 отказах подряд останавливается.
