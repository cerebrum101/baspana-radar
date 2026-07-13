"""T4 (Layer 1) — генерация карточек due diligence ТОЛЬКО из собственных данных.

Запуск:
    python generate_cards.py --limit 5     # проба на 5 ЖК
    python generate_cards.py               # все ЖК со статистикой (батч, медленно)

Ожидает в .env один из ключей:
    GEMINI_API_KEY=...   (aistudio.google.com, бесплатный тир)
    GROQ_API_KEY=...     (console.groq.com, бесплатный тир)

Выход: dd_cards.jsonl  →  затем python load_supabase.py --cards

Правила грунтовки (зашиты в промпт и проверяются кодом):
- модель видит ТОЛЬКО данные нашего снапшота: параметры ЖК, статистику,
  флаги аномалий, фрагменты объявлений. Никаких внешних знаний;
- каждый flag обязан ссылаться на переданный факт; tier для Layer 1 —
  только confirmed (наш расчёт) или no_data;
- невалидный JSON или выдуманные поля → карточка бракуется, ЖК пропускается.
"""
import argparse
import datetime
import json
import os
import time
from pathlib import Path

import httpx

from common import append_jsonl, read_jsonl

OUT = "dd_cards.jsonl"
TODAY = datetime.date.today().isoformat()

PROMPT = """Ты — осторожный аналитик недвижимости. Составь карточку due diligence
жилого комплекса в Астане СТРОГО по данным ниже. Запрещено использовать любые
знания вне этих данных. Если данных мало — так и пиши, не выдумывай.

ДАННЫЕ ЖК:
{complex_json}

СТАТИСТИКА ОБЪЯВЛЕНИЙ (наш снапшот от {today}):
{stats_json}

ФРАГМЕНТЫ ОБЪЯВЛЕНИЙ (до 10 шт.):
{snippets}

Верни ТОЛЬКО валидный JSON без markdown, схема:
{{
  "risk_score": <int 0-100, 0=минимальный риск. Калибровка: сдан+документы+без аномалий ≈ 15-25; строится ≈ +15; нет документов ≈ +15; каждая аномалия ≈ +5-10>,
  "verdict": "<3-5 предложений по-русски: кому подходит, на какую цену ориентироваться (из статистики), главный риск>",
  "strengths": ["<2-4 пункта, каждый опирается на переданный факт>"],
  "weaknesses": ["<2-4 пункта, каждый опирается на переданный факт>"],
  "flags": [
    {{"tier": "confirmed"|"no_data", "title": "<коротко>", "detail": "<факт из данных + что это значит для покупателя>"}}
  ]
}}
Правила: tier=confirmed только для фактов из переданных данных; про отзывы
жильцов и репутацию застройщика всегда один flag с tier=no_data (мы их не
проверяли); никаких других tier не используй."""


def call_llm(prompt):
    gem = os.environ.get("GEMINI_API_KEY")
    groq = os.environ.get("GROQ_API_KEY")
    if gem:
        r = httpx.post(
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "gemini-2.0-flash:generateContent",
            params={"key": gem},
            json={"contents": [{"parts": [{"text": prompt}]}],
                  "generationConfig": {"temperature": 0.2}},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    if groq:
        r = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {groq}"},
            json={"model": "llama-3.3-70b-versatile",
                  "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.2},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    raise SystemExit("Нет GEMINI_API_KEY / GROQ_API_KEY в .env")


def extract_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        text = text[4:] if text.startswith("json") else text
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1])


ALLOWED_TIERS = {"confirmed", "no_data"}


def validate(card):
    if not isinstance(card.get("risk_score"), int) or not 0 <= card["risk_score"] <= 100:
        return "risk_score"
    if not card.get("verdict") or len(card["verdict"]) < 50:
        return "verdict"
    for f in card.get("flags", []):
        if f.get("tier") not in ALLOWED_TIERS:
            return f"flag tier {f.get('tier')!r}"
    return None


def load_env():
    p = Path(".env")
    if p.exists():
        for line in p.read_text().splitlines():
            if line.strip() and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    load_env()

    complexes = {c["slug"]: c for c in read_jsonl("complexes.jsonl")}
    stats = {s["complex_slug"]: s for s in read_jsonl("complex_stats.jsonl")}
    listings = read_jsonl("listings_clean.jsonl")
    snippets = {}
    for l in listings:
        s = l.get("complex_slug")
        if s and l.get("raw_snippet"):
            snippets.setdefault(s, []).append(l["raw_snippet"])

    done = {c["complex_slug"] for c in read_jsonl(OUT)}
    # приоритет: ЖК с наибольшим числом объявлений
    todo = sorted(
        (s for s in stats if s not in done and s in complexes),
        key=lambda s: -stats[s]["n_listings"],
    )
    if args.limit:
        todo = todo[:args.limit]
    print(f"к генерации: {len(todo)} ЖК (готово ранее: {len(done)})")

    ok = bad = 0
    for i, slug in enumerate(todo, 1):
        prompt = PROMPT.format(
            complex_json=json.dumps(complexes[slug], ensure_ascii=False, indent=1),
            stats_json=json.dumps(stats[slug], ensure_ascii=False, indent=1),
            snippets="\n".join(f"- {s}" for s in snippets.get(slug, [])[:10]) or "(нет)",
            today=TODAY,
        )
        try:
            card = extract_json(call_llm(prompt))
        except Exception as e:
            print(f"[{i}] {slug}: LLM/JSON ошибка ({type(e).__name__}) — пропуск")
            bad += 1
            time.sleep(5)
            continue
        err = validate(card)
        if err:
            print(f"[{i}] {slug}: брак ({err}) — пропуск")
            bad += 1
            continue
        append_jsonl(OUT, {
            "complex_slug": slug,
            "layer": 1,
            "risk_score": card["risk_score"],
            "verdict": card["verdict"],
            "strengths": card.get("strengths", []),
            "weaknesses": card.get("weaknesses", []),
            "flags": card["flags"],
            "sources": [{"title": "krisha.kz — страница ЖК",
                         "url": complexes[slug].get("krisha_url")},
                        {"title": f"снапшот Baspana Radar от {TODAY}", "url": None}],
            "generated_at": TODAY,
            "model": "gemini-2.0-flash" if os.environ.get("GEMINI_API_KEY")
                     else "llama-3.3-70b",
        })
        ok += 1
        print(f"[{i}/{len(todo)}] {slug}: ok (risk={card['risk_score']})")
        time.sleep(4)   # бесплатные тиры: ~15 rpm

    print(f"\nготово: {ok}, брак: {bad}. Далее: python load_supabase.py --cards")


if __name__ == "__main__":
    main()
