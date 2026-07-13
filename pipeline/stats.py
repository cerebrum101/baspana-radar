"""Block 4 — статистика и аномалии по ЖК. Оффлайн.

Запуск: python stats.py
Вход:  listings_clean.jsonl, complexes.jsonl
Выход: complex_stats.jsonl

Правила честности: n<8 → low_sample (в приложении статистика помечается
как ненадёжная); аномалии — коды с деталями, не приговоры.
"""
import datetime
import statistics

from common import append_jsonl, read_jsonl

LISTINGS = "listings_clean.jsonl"
COMPLEXES = "complexes.jsonl"
OUT = "complex_stats.jsonl"

TODAY = datetime.date.today().isoformat()
CUR_YEAR = datetime.date.today().year


def pct(sorted_vals, p):
    if not sorted_vals:
        return None
    k = (len(sorted_vals) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def main():
    listings = read_jsonl(LISTINGS)
    complexes = {c["slug"]: c for c in read_jsonl(COMPLEXES)}
    by_slug = {}
    for l in listings:
        s = l.get("complex_slug")
        if s:
            by_slug.setdefault(s, []).append(l)

    open(OUT, "w").close()
    for slug, ls in sorted(by_slug.items()):
        perm2 = sorted(l["price_m2"] for l in ls)
        prices = [l["price"] for l in ls]
        n = len(ls)
        c = complexes.get(slug, {})
        flags = []

        p25, p75 = pct(perm2, 0.25), pct(perm2, 0.75)
        if n >= 8 and p25 and p75 / p25 > 1.6:
            flags.append({
                "code": "high_dispersion",
                "detail": f"разброс цен p75/p25 = {p75 / p25:.2f} — возможен смешанный "
                          f"класс корпусов или проблемные квартиры в продаже",
            })

        apts = c.get("apartments_total")
        if apts and n / apts > 0.10:
            flags.append({
                "code": "listing_pileup",
                "detail": f"в продаже {n} из ~{apts} квартир ({100 * n // apts}%) — "
                          f"массовый выход собственников или нераспроданная первичка",
            })

        urgent_share = sum(1 for l in ls if l.get("urgent")) / n
        if n >= 8 and urgent_share > 0.3:
            flags.append({
                "code": "urgent_share",
                "detail": f"{int(urgent_share * 100)}% объявлений с пометкой «срочно/торг»",
            })

        status = (c.get("status") or "").lower()
        years = [l["year_built"] for l in ls if l.get("year_built")]
        if "строя" in status and years and max(years) <= CUR_YEAR - 2:
            flags.append({
                "code": "stale_complex_data",
                "detail": f"krisha числит ЖК строящимся, но квартиры с годом постройки "
                          f"до {max(years)} — данные страницы ЖК устарели",
            })
        if years and c.get("deadline_declared"):
            import re
            m = re.search(r"(\d{4})", c["deadline_declared"])
            if m and max(years) > int(m.group(1)) + 1:
                flags.append({
                    "code": "possible_delay",
                    "detail": f"заявленный срок сдачи {c['deadline_declared']}, "
                              f"фактические годы постройки до {max(years)} — вероятная "
                              f"задержка сдачи очередей (проверить)",
                })

        append_jsonl(OUT, {
            "complex_slug": slug,
            "snapshot_date": TODAY,
            "n_listings": n,
            "median_m2": round(statistics.median(perm2)),
            "p25_m2": round(p25) if p25 else None,
            "p75_m2": round(p75) if p75 else None,
            "min_price": min(prices),
            "max_price": max(prices),
            "low_sample": n < 8,
            "anomaly_flags": flags,
        })

    print(f"ЖК со статистикой: {len(by_slug)}")
    flagged = sum(1 for line in read_jsonl(OUT) if line["anomaly_flags"])
    print(f"ЖК с аномалиями: {flagged}")


if __name__ == "__main__":
    main()
