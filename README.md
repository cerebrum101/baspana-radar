# Baspana Radar — веб (Next.js)

Серверный рендеринг (SEO по каждому ЖК), официальный клиент Supabase,
бесплатный деплой на Vercel. Данные читаются из вашей базы Supabase
(anon-ключ + public-read RLS).

## Запуск локально

```bash
cd web-next
npm install
npm run dev
```

Откройте http://localhost:3000 . `.env.local` уже создан с вашими
public-значениями Supabase.

## Структура

- `app/page.js` — главная: фильтры (район, комнаты, цена, сортировка) + сетка
  объявлений; серверный компонент, читает параметры из URL.
- `app/complex/[slug]/page.js` — страница ЖК с реальным URL (для Google):
  статистика цен, карточка риска, объявления. `generateMetadata` даёт
  SEO-заголовок и описание.
- `app/components/Filters.js` — клиентский компонент, меняет query-параметры.
- `app/components/ListingCard.js` — карточка объявления с бейджем отклонения
  от справедливой цены.
- `lib/supabase.js` — read-only клиент. `lib/format.js` — форматирование ₸ и
  логика бейджа.

Данные обновляются через ISR: `export const revalidate = 300` (не чаще раза
в 5 минут страница пересобирается свежими данными из Supabase).

## Деплой (бесплатно, Vercel)

1. Запушьте проект в GitHub (или только папку `web-next`).
2. vercel.com → New Project → импортируйте репозиторий → Root Directory:
   `web-next` (если пушили весь проект).
3. Environment Variables — добавьте те же две, что в `.env.local`:
   `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
4. Deploy. Получите публичный URL.

Cloudflare Pages / Netlify тоже поддерживают Next.js — процесс аналогичен.

## Что дальше

- Пагинация / бесконечная лента на главной (сейчас первые 60).
- Карта (2ГИС/OSM), избранное, история цен по ЖК.
- Слой новостей/репутации застройщика (Layer 2) — отдельные таблицы + флаги.
