"""Block 1 — entity spine: все ЖК Астаны с krisha.kz.

Запуск:
    python scrape_complexes.py --sample   # 5 ЖК, проверка парсера
    python scrape_complexes.py            # полный проход (~30-60 мин)

Выход: complexes.jsonl (+ чекпоинт complexes.ckpt.json, кэш raw/)
Стратегия парсинга: текстовая — вытаскиваем пары "метка → значение" из
нормализованного текста страницы, а не из CSS-классов. Переживает
косметические изменения вёрстки.
"""
import argparse
import re
import sys

from selectolax.parser import HTMLParser

from common import Fetcher, append_jsonl, load_checkpoint, read_jsonl, save_checkpoint

BASE = "https://krisha.kz"
CKPT = "complexes.ckpt.json"
OUT = "complexes.jsonl"

SLUG_RE = re.compile(r"/complex/show/(?:([a-z-]+)/)?([a-z0-9-]+)/?$")

# метки на странице ЖК → поля таблицы
LABELS = {
    "Класс жилья": "class",
    "Этажность": "floors",
    "Высота потолков": "ceiling_raw",
    "Количество квартир": "apartments_raw",
    "Статус строительства": "status",
    "Срок сдачи": "deadline_declared",
    "Расположение": "address",
    "Застройщик": "developer_brand",
    "Разрешения": "permits",
}


def text_lines(html):
    tree = HTMLParser(html)
    for sel in ("script", "style", "noscript"):
        for node in tree.css(sel):
            node.decompose()
    body = tree.body
    if body is None:
        return [], tree
    raw = body.text(separator="\n")
    lines = [l.strip() for l in raw.split("\n")]
    return [l for l in lines if l], tree


def discover_slugs(fetcher):
    """Каталог /complex/search/astana/ + пагинация. Собираем все слуги."""
    slugs = {}
    page = 1
    empty_streak = 0
    while page < 100:
        url = f"{BASE}/complex/search/astana/?page={page}"
        html = fetcher.get(url)
        if not html:
            break
        found = 0
        tree = HTMLParser(html)
        for a in tree.css("a"):
            href = a.attributes.get("href") or ""
            m = SLUG_RE.search(href.split("?")[0])
            if m:
                city, slug = m.group(1) or "astana", m.group(2)
                if slug not in slugs:
                    slugs[slug] = {"city": city, "url": f"{BASE}/complex/show/{city}/{slug}/"}
                    found += 1
        print(f"каталог стр. {page}: +{found} ЖК (всего {len(slugs)})")
        empty_streak = empty_streak + 1 if found == 0 else 0
        if empty_streak >= 2:
            break
        page += 1
    return slugs


def parse_complex(html, slug, url, city):
    lines, tree = text_lines(html)

    def after(label):
        for i, l in enumerate(lines):
            if l == label and i + 1 < len(lines):
                return lines[i + 1]
        return None

    h1 = tree.css_first("h1")
    name = h1.text(strip=True) if h1 else (lines[0] if lines else slug)
    name = re.sub(r"\s+в\s+(Астане|Нур-Султане)$", "", name)

    joined = "\n".join(lines)
    rec = {"slug": slug, "city": city, "name": name, "krisha_url": url}

    for label, field in LABELS.items():
        rec[field] = after(label)

    m = re.search(r"от\s+([\d\s ]+)\s*[₸〒]\s*за\s*м²", joined)
    rec["price_m2_listed"] = int(re.sub(r"\D", "", m.group(1))) if m else None
    m = re.search(r"актуальная цена на\s+([\d]+\s+\w+)", joined)
    rec["price_m2_date"] = m.group(1) if m else None

    # производные
    if rec.get("ceiling_raw"):
        m = re.search(r"([\d.,]+)", rec["ceiling_raw"])
        rec["ceiling_m"] = float(m.group(1).replace(",", ".")) if m else None
    if rec.get("apartments_raw"):
        m = re.search(r"(\d+)", rec["apartments_raw"])
        rec["apartments_total"] = int(m.group(1)) if m else None
    rec.pop("ceiling_raw", None)
    rec.pop("apartments_raw", None)

    if rec.get("address"):
        m = re.search(r"(Есильский|Нура|Сарайшык|Сарыарка|Алматы|Байконур)", rec["address"])
        rec["district"] = m.group(1) if m else None

    # юрлицо застройщика из блока разрешений, если отличается от бренда
    m = re.search(r"застройщик\s*[–-]\s*(ТОО\s*«[^»]+»)", joined)
    rec["developer_legal"] = m.group(1) if m else rec.get("developer_brand")

    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true", help="только 5 ЖК — проверка парсера")
    args = ap.parse_args()

    fetcher = Fetcher()
    ckpt = load_checkpoint(CKPT, {"done": []})
    done = set(ckpt["done"])

    slugs = discover_slugs(fetcher)
    if not slugs:
        sys.exit("Каталог не отдал ни одного ЖК — проверьте доступность krisha.kz")

    todo = [s for s in slugs if s not in done]
    if args.sample:
        todo = todo[:5]
    print(f"\nЖК к обработке: {len(todo)} (пропущено по чекпоинту: {len(done)})\n")

    for i, slug in enumerate(todo, 1):
        info = slugs[slug]
        html = fetcher.get(info["url"])
        if not html:
            print(f"[{i}] {slug}: страница недоступна, пропуск")
            continue
        rec = parse_complex(html, slug, info["url"], info["city"])
        append_jsonl(OUT, rec)
        done.add(slug)
        save_checkpoint(CKPT, {"done": sorted(done)})
        filled = sum(1 for v in rec.values() if v)
        print(f"[{i}/{len(todo)}] {slug}: {rec['name']} · заполнено полей {filled}/{len(rec)}")

    print(f"\nГотово. {fetcher.stats()}")
    if args.sample:
        print("\n--sample: проверьте записи в complexes.jsonl. Если поля пустые —")
        print("пришлите один файл из raw/ для починки парсера, полный прогон не запускайте.")


if __name__ == "__main__":
    main()
