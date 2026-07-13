"""T4b — Layer-2 карточки: собранные вручную источники + LLM-структурирование.

Запуск:
    python generate_cards_l2.py                    # все ЖК с папкой в sources/
    python generate_cards_l2.py --slug vremena-goda-vesna

Вход:  sources/<slug>/*.txt (см. sources/README.md), complexes.jsonl,
       complex_stats.jsonl, а также существующий dd_cards.jsonl (L2
       перезаписывает L1-карточку того же ЖК).
Выход: dd_cards.jsonl (upsert по slug)

Гарантии, которые enforce'ит КОД (не только промпт):
- каждый flag обязан ссылаться на url из переданных источников, иначе брак;
- tier=confirmed разрешён только если цитируемый источник type=official|news;
- tier=reported требует ≥2 разных url; при одном — автопонижение до rumor;
- имена частных лиц в тексте карточки → брак.
"""
import argparse
import datetime
import json
import re
import time
from pathlib import Path

from common import read_jsonl
from generate_cards import call_llm, extract_json, load_env

SRC_DIR = Path("sources")
OUT = "dd_cards.jsonl"
TODAY = datetime.date.today().isoformat()

PROMPT = """Ты — осторожный аналитик недвижимости. По собранным источникам составь
карточку due diligence ЖК в Астане. Используй ТОЛЬКО переданные источники и
данные снапшота — никаких внешних знаний.

ДАННЫЕ ЖК И СТАТИСТИКА НАШЕГО СНАПШОТА:
{context_json}

ИСТОЧНИКИ (нумерованы):
{sources_block}

Верни ТОЛЬКО валидный JSON:
{{
  "risk_score": <int 0-100, калибровка: сдан+без жалоб ≈ 15-25; подтверждённые проблемы стройки/документов +15-30; массовые жалобы жильцов +10-20>,
  "verdict": "<4-6 предложений: кому подходит, ценовой ориентир из статистики, главные риски и их достоверность>",
  "strengths": ["<2-5 пунктов с опорой на источники/данные>"],
  "weaknesses": ["<2-5 пунктов с опорой на источники/данные>"],
  "flags": [
    {{"tier": "confirmed"|"reported"|"rumor"|"no_data",
      "title": "<коротко>",
      "detail": "<утверждение + что это значит для покупателя>",
      "source_urls": ["<url источника №N>", ...]}}
  ]
}}
Правила достоверности (нарушение = карточка бракуется):
- confirmed: только официальные документы или публикации СМИ (type official/news);
- reported: жалоба минимум из ДВУХ независимых источников — укажи оба url;
- rumor: единичное упоминание из отзывов/форумов;
- no_data: обязательный флаг для важных тем, которые источники НЕ покрывают
  (например: качество отопления зимой, лифты, управляющая компания);
- НИКОГДА не называй имена частных лиц. Названия компаний — можно."""

TIER_OK = {"confirmed", "reported", "rumor", "no_data"}
NAME_RE = re.compile(r"\b[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(ов|ев|ин|ова|ева|ина|кызы|улы)\b")


def parse_source_file(path):
    text = path.read_text(encoding="utf-8")
    head, _, body = text.partition("---")
    meta = {}
    for line in head.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip().lower()] = v.strip()
    return {"url": meta.get("url", ""), "title": meta.get("title", path.name),
            "type": meta.get("type", "reviews"), "date": meta.get("date"),
            "text": body.strip()[:4000]}


def validate(card, sources):
    urls = {s["url"] for s in sources}
    type_by_url = {s["url"]: s["type"] for s in sources}
    if not isinstance(card.get("risk_score"), int):
        return "risk_score"
    full_text = json.dumps(card, ensure_ascii=False)
    if NAME_RE.search(full_text):
        return "личное имя в тексте карточки"
    for f in card.get("flags", []):
        if f.get("tier") not in TIER_OK:
            return f"tier {f.get('tier')!r}"
        cited = [u for u in f.get("source_urls", []) if u in urls]
        if f["tier"] == "no_data":
            continue
        if not cited:
            return f"flag «{f.get('title')}» без валидного источника"
        if f["tier"] == "confirmed":
            if not any(type_by_url[u] in ("official", "news") for u in cited):
                return f"confirmed без official/news источника: «{f.get('title')}»"
        if f["tier"] == "reported" and len(set(cited)) < 2:
            f["tier"] = "rumor"   # автопонижение, не брак
    return None


def upsert_card(record):
    cards = [c for c in read_jsonl(OUT) if c["complex_slug"] != record["complex_slug"]]
    cards.append(record)
    with open(OUT, "w", encoding="utf-8") as fh:
        for c in cards:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug")
    args = ap.parse_args()
    load_env()

    complexes = {c["slug"]: c for c in read_jsonl("complexes.jsonl")}
    stats = {s["complex_slug"]: s for s in read_jsonl("complex_stats.jsonl")}

    slugs = [args.slug] if args.slug else [
        p.name for p in SRC_DIR.iterdir() if p.is_dir()
    ]
    for slug in slugs:
        folder = SRC_DIR / slug
        files = sorted(folder.glob("*.txt"))
        if not files:
            print(f"{slug}: нет источников, пропуск")
            continue
        sources = [parse_source_file(p) for p in files]
        sources_block = "\n\n".join(
            f"[{i + 1}] url: {s['url']}\ntype: {s['type']} · {s['title']}"
            f"{' · ' + s['date'] if s['date'] else ''}\n{s['text']}"
            for i, s in enumerate(sources)
        )
        context = {"complex": complexes.get(slug, {"slug": slug}),
                   "stats": stats.get(slug)}
        prompt = PROMPT.format(
            context_json=json.dumps(context, ensure_ascii=False, indent=1),
            sources_block=sources_block,
        )
        try:
            card = extract_json(call_llm(prompt))
        except Exception as e:
            print(f"{slug}: LLM/JSON ошибка ({type(e).__name__})")
            continue
        err = validate(card, sources)
        if err:
            print(f"{slug}: брак — {err}")
            continue
        # source_urls флагов → форма приложения {title,url}
        by_url = {s["url"]: s["title"] for s in sources}
        for f in card["flags"]:
            us = f.pop("source_urls", [])
            f["source"] = ({"title": by_url.get(us[0], us[0]), "url": us[0]}
                           if us else None)
            if len(us) > 1:
                f["extra_sources"] = [{"title": by_url.get(u, u), "url": u}
                                      for u in us[1:]]
        upsert_card({
            "complex_slug": slug,
            "layer": 2,
            "risk_score": card["risk_score"],
            "verdict": card["verdict"],
            "strengths": card.get("strengths", []),
            "weaknesses": card.get("weaknesses", []),
            "flags": card["flags"],
            "sources": [{"title": s["title"], "url": s["url"]} for s in sources],
            "generated_at": TODAY,
            "model": "layer2",
        })
        print(f"{slug}: ok (risk={card['risk_score']}, источников={len(sources)})")
        time.sleep(4)

    print(f"\nДалее: python load_supabase.py --cards")


if __name__ == "__main__":
    main()
