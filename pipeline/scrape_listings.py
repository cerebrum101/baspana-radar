"""Block 2 — все объявления о продаже квартир в Астане (search-страницы).

Запуск:
    python scrape_listings.py --sample        # 2 страницы, диагностика парсера
    python scrape_listings.py                 # полный проход (~1.5-3 ч)
    python scrape_listings.py --max-pages 500 # ограниченный проход

Выход: listings_raw.jsonl (+ чекпоинт listings.ckpt.json, кэш raw/)

Двухуровневая стратегия парсинга:
  A. embedded JSON: krisha кладёт данные объявлений в window.data /
     digitalData — если найдём, берём оттуда (надёжнее);
  B. HTML-карточки: заголовок "2-комнатная квартира · 48 м² · 1/9 этаж",
     цена, адрес, ссылка на ЖК. Проверено на реальной выдаче.
PII: имена продавцов НЕ сохраняются — только тип (хозяин/агент/компания).
"""
import argparse
import re

from selectolax.parser import HTMLParser

from common import Fetcher, append_jsonl, load_checkpoint, save_checkpoint

BASE = "https://krisha.kz"
SEARCH = BASE + "/prodazha/kvartiry/astana/?page={page}"
CKPT = "listings.ckpt.json"
OUT = "listings_raw.jsonl"

TITLE_RE = re.compile(
    r"(\d+)-комнатная квартира\s*·\s*([\d.,]+)\s*м²(?:\s*·\s*(\d+)/(\d+)\s*этаж)?"
)
PRICE_RE = re.compile(r"([\d\s ]{7,})\s*[₸〒]")
ID_RE = re.compile(r"/a/show/(\d+)")
COMPLEX_LINK_RE = re.compile(r"/complex/show/(?:[a-z-]+/)?([a-z0-9-]+)/?")
COMPLEX_TEXT_RE = re.compile(r"жил\.\s*комплекс\s+([^,]+)")
YEAR_RE = re.compile(r"(\d{4})\s*г\.п\.")
DISTRICT_RE = re.compile(r"(Есильский|Нура|Сарайшык|Сарыарка|Алматы|Байконур)\s*р-н")
TOTAL_RE = re.compile(r"Найдено\s+([\d\s ]+)\s+объявлен")

SELLER_TYPES = [
    ("Хозяин недвижимости", "owner"),
    ("Крыша Агент", "agent"),
    ("Специалист", "specialist"),
    ("Компания", "company"),
]


def try_embedded_json(html):
    """Стратегия A: ищем JSON с объявлениями в скриптах."""
    m = re.search(r"window\.data\s*=\s*(\{.+?\});?\s*\n", html, re.DOTALL)
    if not m:
        return None
    try:
        import json

        data = json.loads(m.group(1))
    except Exception:
        return None
    # структура может отличаться — ищем список с ключами, похожими на объявления
    def find_adverts(node, depth=0):
        if depth > 4:
            return None
        if isinstance(node, list) and node and isinstance(node[0], dict):
            keys = set(node[0].keys())
            if {"id", "price"} <= keys or {"id", "title"} <= keys:
                return node
        if isinstance(node, dict):
            for v in node.values():
                r = find_adverts(v, depth + 1)
                if r:
                    return r
        return None

    return find_adverts(data)


def parse_cards(html):
    """Стратегия B: HTML-карточки выдачи."""
    tree = HTMLParser(html)
    for sel in ("script", "style", "noscript"):
        for node in tree.css(sel):
            node.decompose()

    # группируем по объявлению: ищем контейнеры, содержащие ссылку /a/show/
    seen = {}
    for a in tree.css("a"):
        href = a.attributes.get("href") or ""
        m = ID_RE.search(href)
        if not m:
            continue
        lid = m.group(1)
        title = a.text(strip=True)
        if not TITLE_RE.search(title or ""):
            continue  # это ссылка-картинка, а не заголовок
        # поднимаемся к контейнеру карточки (3-5 уровней)
        node = a
        for _ in range(6):
            if node.parent is None:
                break
            node = node.parent
            text = node.text(separator=" ", strip=True)
            if PRICE_RE.search(text) and len(text) > 80:
                break
        seen[lid] = (title, node.text(separator="\n", strip=True), node)

    out = []
    for lid, (title, text, node) in seen.items():
        rec = {"id": lid, "url": f"{BASE}/a/show/{lid}"}
        tm = TITLE_RE.search(title)
        rec["rooms"] = int(tm.group(1))
        rec["area"] = float(tm.group(2).replace(",", "."))
        rec["floor"] = int(tm.group(3)) if tm.group(3) else None
        rec["floors_total"] = int(tm.group(4)) if tm.group(4) else None

        pm = PRICE_RE.search(text)
        rec["price"] = int(re.sub(r"\D", "", pm.group(1))) if pm else None

        cm = COMPLEX_TEXT_RE.search(text)
        rec["complex_name_raw"] = cm.group(1).strip() if cm else None
        rec["complex_slug"] = None
        for a2 in node.css("a"):
            h2 = a2.attributes.get("href") or ""
            m2 = COMPLEX_LINK_RE.search(h2.split("?")[0])
            if m2:
                rec["complex_slug"] = m2.group(1)
                break

        ym = YEAR_RE.search(text)
        rec["year_built"] = int(ym.group(1)) if ym else None
        dm = DISTRICT_RE.search(text)
        rec["district"] = dm.group(1) if dm else None
        rec["urgent"] = "Срочно" in text

        rec["seller_type"] = None
        for marker, code in SELLER_TYPES:
            if marker in text:
                rec["seller_type"] = code
                break

        # фрагмент описания (после строки с "жил. комплекс"), без имён
        lines = text.split("\n")
        snippet = ""
        for l in lines:
            if "жил. комплекс" in l or "г.п." in l:
                snippet = l[:400]
                break
        rec["raw_snippet"] = snippet

        if rec["price"] and rec["area"]:
            out.append(rec)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true")
    ap.add_argument("--max-pages", type=int, default=0)
    args = ap.parse_args()

    fetcher = Fetcher()
    ckpt = load_checkpoint(CKPT, {"page": 1, "ids": []})
    known_ids = set(ckpt["ids"])
    page = ckpt["page"]
    total_expected = None
    empty_streak = 0
    max_pages = 2 if args.sample else (args.max_pages or 10_000)
    pages_done = 0

    while pages_done < max_pages:
        html = fetcher.get(SEARCH.format(page=page), use_cache=args.sample)
        if not html:
            break

        if total_expected is None:
            tm = TOTAL_RE.search(html)
            if tm:
                total_expected = int(re.sub(r"\D", "", tm.group(1)))
                print(f"krisha сообщает: {total_expected} объявлений "
                      f"(~{total_expected // 20 + 1} страниц)\n")

        adverts = try_embedded_json(html)
        strategy = "A:json" if adverts else "B:html"
        records = parse_cards(html) if not adverts else None
        if adverts:
            # JSON-структуру логируем в sample-режиме и падаем обратно на HTML,
            # пока не подтвердим маппинг полей
            if args.sample:
                print(f"  [диагностика] embedded JSON найден, ключи: "
                      f"{sorted(adverts[0].keys())[:15]}")
            records = parse_cards(html)

        new = [r for r in records if r["id"] not in known_ids]
        for r in new:
            append_jsonl(OUT, r)
            known_ids.add(r["id"])

        print(f"стр. {page} [{strategy}]: карточек {len(records)}, новых {len(new)}, "
              f"всего {len(known_ids)}")

        if args.sample:
            filled = lambda f: sum(1 for r in records if r.get(f) is not None)
            n = max(1, len(records))
            print("\n  --- диагностика заполненности полей ---")
            for f in ("price", "area", "rooms", "floor", "complex_slug",
                      "complex_name_raw", "year_built", "district", "seller_type"):
                print(f"  {f:18s} {filled(f)}/{len(records)} ({100 * filled(f) // n}%)")

        empty_streak = empty_streak + 1 if not new else 0
        if empty_streak >= 3:
            print("3 страницы без новых объявлений — конец выдачи.")
            break

        page += 1
        pages_done += 1
        save_checkpoint(CKPT, {"page": page, "ids": sorted(known_ids)})

    save_checkpoint(CKPT, {"page": page, "ids": sorted(known_ids)})
    print(f"\nГотово: {len(known_ids)} объявлений в {OUT}. {fetcher.stats()}")
    if args.sample:
        print("\n--sample: если complex_slug/price сильно ниже 90% — пришлите"
              " один HTML из raw/, починю парсер до полного прогона.")


if __name__ == "__main__":
    main()
