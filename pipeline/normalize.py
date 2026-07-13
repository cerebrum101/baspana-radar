"""Block 3 — нормализация. Оффлайн, сети не касается.

Запуск: python normalize.py
Вход:  listings_raw.jsonl, complexes.jsonl
Выход: listings_clean.jsonl + отчёт в консоль

Делает: типы, price_m2, дедупликацию, fuzzy-привязку ЖК по названию
(для объявлений без ссылки на ЖК), санитарные проверки.
PII-гарантия: в выходном файле нет ни одного поля с именем/телефоном.
"""
import re
from collections import defaultdict

from common import append_jsonl, read_jsonl

RAW = "listings_raw.jsonl"
COMPLEXES = "complexes.jsonl"
OUT = "listings_clean.jsonl"

ALLOWED_FIELDS = {
    "id", "complex_slug", "complex_name_raw", "rooms", "area", "floor",
    "floors_total", "price", "price_m2", "year_built", "condition",
    "address", "district", "seller_type", "urgent", "dup_suspect",
    "url", "raw_snippet",
}


def norm_name(s):
    """«ЖК "Времена Года. Весна-2"» → 'времена года весна' (для матчинга)."""
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r"жк|жил\.?\s*комплекс|бигвилль|мжк", " ", s)
    s = re.sub(r"[«»\"'.,()–-]", " ", s)
    s = re.sub(r"\b\d+\b", " ", s)          # номера очередей
    return re.sub(r"\s+", " ", s).strip()


def build_name_index(complexes):
    idx = {}
    for c in complexes:
        idx[norm_name(c["name"])] = c["slug"]
    return idx


def match_slug(name_raw, idx):
    n = norm_name(name_raw)
    if not n:
        return None
    if n in idx:
        return idx[n]
    # частичное совпадение: нормализованное имя объявления начинается с имени ЖК
    for key, slug in idx.items():
        if key and (n.startswith(key) or key.startswith(n)):
            return slug
    return None


def main():
    raw = read_jsonl(RAW)
    complexes = read_jsonl(COMPLEXES)
    if not raw:
        raise SystemExit(f"{RAW} пуст — сначала запустите scrape_listings.py")
    idx = build_name_index(complexes) if complexes else {}
    known_slugs = {c["slug"] for c in complexes}

    stats = defaultdict(int)
    seen_ids = set()
    fingerprints = {}
    out = []

    for r in raw:
        stats["total"] += 1
        if r["id"] in seen_ids:
            stats["dropped_repeat_id"] += 1
            continue
        seen_ids.add(r["id"])

        # типы и обязательные поля
        try:
            r["price"] = int(r["price"])
            r["area"] = float(r["area"])
            r["rooms"] = int(r["rooms"])
        except (TypeError, ValueError):
            stats["dropped_bad_fields"] += 1
            continue
        if r["price"] < 3_000_000 or r["area"] < 10:
            stats["dropped_implausible"] += 1
            continue
        r["price_m2"] = round(r["price"] / r["area"])

        # привязка к ЖК
        if r.get("complex_slug") and r["complex_slug"] not in known_slugs:
            stats["slug_unknown_kept"] += 1  # ЖК не из каталога — оставляем, FK нет
        if not r.get("complex_slug") and r.get("complex_name_raw"):
            matched = match_slug(r["complex_name_raw"], idx)
            if matched:
                r["complex_slug"] = matched
                stats["fuzzy_matched"] += 1
            else:
                stats["fuzzy_failed"] += 1

        # дедуп: тот же ЖК/имя + комнаты + площадь ±0.5 м² + цена ±2%
        key = (
            r.get("complex_slug") or norm_name(r.get("complex_name_raw")),
            r["rooms"],
            round(r["area"] * 2) / 2,
        )
        r["dup_suspect"] = False
        if key in fingerprints:
            for prev_price in fingerprints[key]:
                if abs(prev_price - r["price"]) / prev_price < 0.02:
                    r["dup_suspect"] = True
                    stats["dup_suspect"] += 1
                    break
            fingerprints[key].append(r["price"])
        else:
            fingerprints[key] = [r["price"]]

        clean = {k: r.get(k) for k in ALLOWED_FIELDS}
        out.append(clean)

    # перезаписываем выход целиком (идемпотентно)
    open(OUT, "w").close()
    for r in out:
        append_jsonl(OUT, r)

    print(f"вход: {stats['total']}, выход: {len(out)}")
    for k in sorted(stats):
        if k != "total":
            print(f"  {k}: {stats[k]}")
    linked = sum(1 for r in out if r.get("complex_slug"))
    print(f"привязано к ЖК: {linked}/{len(out)} ({100 * linked // max(1, len(out))}%)")


if __name__ == "__main__":
    main()
