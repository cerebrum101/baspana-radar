"""Block 5 — загрузка в Supabase. Идемпотентные upsert'ы.

Запуск:
    python load_supabase.py            # complexes + listings + stats
    python load_supabase.py --cards    # дополнительно dd_cards.jsonl

Ожидает .env в этой папке (или переменные окружения):
    SUPABASE_URL=https://xxxx.supabase.co
    SUPABASE_SERVICE_KEY=eyJ...   (service_role, НЕ anon)
"""
import argparse
import datetime
import os
from pathlib import Path

from common import read_jsonl


def load_env():
    p = Path(".env")
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def chunked(seq, size=500):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


COMPLEX_FIELDS = {
    "slug", "name", "city", "district", "class", "developer_brand",
    "developer_legal", "status", "deadline_declared", "floors", "ceiling_m",
    "apartments_total", "price_m2_listed", "price_m2_date", "permits",
    "address", "krisha_url",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cards", action="store_true")
    args = ap.parse_args()

    load_env()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise SystemExit("Нет SUPABASE_URL / SUPABASE_SERVICE_KEY (в .env или окружении)")

    from supabase import create_client
    sb = create_client(url, key)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()

    complexes = read_jsonl("complexes.jsonl")
    rows = [{k: c.get(k) for k in COMPLEX_FIELDS} for c in complexes]
    for batch in chunked(rows):
        sb.table("complexes").upsert(batch).execute()
    print(f"complexes: {len(rows)}")

    listings = read_jsonl("listings_clean.jsonl")
    known = {c["slug"] for c in complexes}
    today = datetime.date.today().isoformat()
    lrows = []
    for l in listings:
        row = dict(l)
        if row.get("complex_slug") not in known:
            row["complex_slug"] = None       # нет FK — не роняем вставку
        row["last_seen"] = today
        lrows.append(row)
    for batch in chunked(lrows):
        sb.table("listings").upsert(batch).execute()
    print(f"listings: {len(lrows)}")

    stats = read_jsonl("complex_stats.jsonl")
    stats = [s for s in stats if s["complex_slug"] in known]
    for batch in chunked(stats):
        sb.table("complex_stats").upsert(batch).execute()
    print(f"complex_stats: {len(stats)}")

    if args.cards:
        cards = read_jsonl("dd_cards.jsonl")
        cards = [c for c in cards if c["complex_slug"] in known]
        for batch in chunked(cards):
            sb.table("dd_cards").upsert(batch).execute()
        print(f"dd_cards: {len(cards)}")

    sb.table("scrape_runs").insert({
        "kind": "full_load",
        "started_at": started,
        "finished_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "pages": None,
        "items": len(lrows),
        "notes": f"complexes={len(rows)} stats={len(stats)}",
    }).execute()
    print("scrape_runs: записан прогон. Готово.")


if __name__ == "__main__":
    main()
