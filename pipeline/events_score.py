"""T7 — инфраструктурный аплифт по ЖК из events.json.

Запуск: python events_score.py
Вход:  events.json, complexes.jsonl
Выход: complex_events.jsonl  {complex_slug, uplift_pct, events: [...]}

v1: привязка через near_slugs (ручная). Когда появятся координаты ЖК —
включится distance-decay (код готов ниже). Аплифты — открытые допущения
(см. events.json), задисконтированные статусом проекта.
"""
import json
import math

from common import append_jsonl, read_jsonl

EVENTS = "events.json"
OUT = "complex_events.jsonl"


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def event_uplift(ev, dist_m, discount):
    if dist_m is None:
        base = ev["uplift_pct_near"] * 0.7  # ручная привязка = «где-то рядом»
    elif dist_m <= ev["near_m"]:
        base = ev["uplift_pct_near"]
    elif dist_m <= ev.get("mid_m", 0):
        base = ev["uplift_pct_mid"]
    else:
        return 0.0
    return base * discount


def main():
    cfg = json.loads(open(EVENTS, encoding="utf-8").read())
    discounts = cfg["status_discount"]
    events = [e for e in cfg["events"] if not e["id"].startswith("template")]
    complexes = read_jsonl("complexes.jsonl")

    open(OUT, "w").close()
    scored = 0
    for c in complexes:
        hits = []
        for ev in events:
            disc = discounts.get(ev["status"], 0.5)
            dist = None
            if c.get("lat") and ev.get("lat"):
                dist = haversine_m(c["lat"], c["lng"], ev["lat"], ev["lng"])
                if dist > ev.get("mid_m", ev["near_m"]):
                    continue
            elif c["slug"] not in ev.get("near_slugs", []):
                continue
            up = event_uplift(ev, dist, disc)
            if up > 0:
                hits.append({
                    "event_id": ev["id"],
                    "title": ev["title"],
                    "status": ev["status"],
                    "uplift_pct": round(up, 1),
                    "distance_m": round(dist) if dist else None,
                    "assumption": f"базовый эффект {ev['uplift_pct_near']}% "
                                  f"(допущение из литературы) × дисконт статуса {disc}",
                    "sources": ev.get("sources", []),
                })
        if hits:
            total = round(min(sum(h["uplift_pct"] for h in hits), 15), 1)
            append_jsonl(OUT, {"complex_slug": c["slug"],
                               "uplift_pct": total, "events": hits})
            scored += 1
    print(f"ЖК с инфраструктурным аплифтом: {scored} "
          f"(события: {len(events)}; шаблоны не считаются)")
    print("Пополняйте events.json из новостей акимата — это ручная курация.")


if __name__ == "__main__":
    main()
