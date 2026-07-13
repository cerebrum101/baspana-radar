"""T7 — оценка галлюцинаций в карточках (LLM-судья + правила).

Запуск: python eval_cards.py            (нужен GEMINI/GROQ ключ в .env)
Вход:  dd_cards.jsonl + те же входы, что видел генератор
Выход: eval_report.md — таблица: карточек проверено, утверждений всего,
       подтверждено входными данными / не подтверждено (= галлюцинация).

Метод: для каждого flag и каждого пункта strengths/weaknesses судья
получает ИСХОДНЫЕ ДАННЫЕ карточки и утверждение, отвечает строго
supported / unsupported / partial. Это и есть число для METHODOLOGY.md.
"""
import datetime
import json
import time
from pathlib import Path

from common import read_jsonl
from generate_cards import call_llm, load_env

JUDGE = """Ты — строгий проверяющий. Дано УТВЕРЖДЕНИЕ из аналитической карточки и
ИСХОДНЫЕ ДАННЫЕ, из которых карточка генерировалась. Ответь одним словом:
supported  — утверждение прямо следует из данных;
partial    — частично следует, но есть приукрашивание/детали не из данных;
unsupported — в данных этого нет.

ИСХОДНЫЕ ДАННЫЕ:
{inputs}

УТВЕРЖДЕНИЕ: {claim}

Ответ (одно слово):"""


def gather_inputs(slug, complexes, stats, snippets, sources_dir):
    parts = {
        "complex": complexes.get(slug),
        "stats": stats.get(slug),
        "snippets": snippets.get(slug, [])[:10],
    }
    folder = Path(sources_dir) / slug
    if folder.is_dir():
        parts["sources"] = [p.read_text(encoding="utf-8")[:3000]
                            for p in sorted(folder.glob("*.txt"))]
    return json.dumps(parts, ensure_ascii=False)[:12000]


def main():
    load_env()
    cards = read_jsonl("dd_cards.jsonl")
    complexes = {c["slug"]: c for c in read_jsonl("complexes.jsonl")}
    stats = {s["complex_slug"]: s for s in read_jsonl("complex_stats.jsonl")}
    snippets = {}
    for l in read_jsonl("listings_clean.jsonl"):
        if l.get("complex_slug") and l.get("raw_snippet"):
            snippets.setdefault(l["complex_slug"], []).append(l["raw_snippet"])

    rows = []
    counts = {"supported": 0, "partial": 0, "unsupported": 0, "error": 0}
    for card in cards:
        slug = card["complex_slug"]
        inputs = gather_inputs(slug, complexes, stats, snippets, "sources")
        claims = []
        for f in card.get("flags", []):
            if f.get("tier") != "no_data":
                claims.append(("flag", f"{f['title']}: {f['detail']}"))
        claims += [("strength", s) for s in card.get("strengths", [])]
        claims += [("weakness", s) for s in card.get("weaknesses", [])]

        for kind, claim in claims:
            try:
                ans = call_llm(JUDGE.format(inputs=inputs, claim=claim))
                verdict = ans.strip().split()[0].lower()
                if verdict not in counts:
                    verdict = "partial"
            except Exception:
                verdict = "error"
            counts[verdict] += 1
            rows.append((slug, kind, verdict, claim[:90]))
            time.sleep(4)
        print(f"{slug}: {len(claims)} утверждений проверено")

    total = sum(counts.values()) or 1
    lines = [
        f"# Оценка галлюцинаций · {datetime.date.today().isoformat()}",
        "",
        f"Карточек: {len(cards)} · утверждений: {total}",
        "",
        "| вердикт | шт | % |",
        "|---|---|---|",
    ]
    for k in ("supported", "partial", "unsupported", "error"):
        lines.append(f"| {k} | {counts[k]} | {100 * counts[k] // total}% |")
    lines += ["", "## Не подтверждённые утверждения (разобрать руками)", ""]
    for slug, kind, verdict, claim in rows:
        if verdict == "unsupported":
            lines.append(f"- **{slug}** [{kind}] {claim}")
    Path("eval_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\neval_report.md готов: unsupported = "
          f"{100 * counts['unsupported'] // total}%")


if __name__ == "__main__":
    main()
