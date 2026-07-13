"""T3 — hedonic-модель справедливой цены (₸/м²).

Запуск: python train_valuation.py          (нужно: pip install scikit-learn)
Вход:  listings_clean.jsonl, complexes.jsonl
Выход: listings_valued.jsonl  — listings_clean + fair_m2, deviation_pct
       valuation_report.txt   — метрики и важность признаков

Модель: GradientBoostingRegressor на price/m² по признакам:
area, rooms, floor, floors_total, floor_ratio, year_built, district,
complex_slug (target-encoded медианой ЖК), class ЖК.

Честность:
- метрики считаются на отложенной выборке (20%), не на трейне;
- если MAE хуже наивного базлайна (медиана ЖК) — скрипт честно говорит
  использовать базлайн и НЕ записывает предсказания модели;
- deviation_pct = (fair - asked)/fair: >0 — просят меньше справедливой.
"""
import datetime
import json
import statistics

from common import append_jsonl, read_jsonl

LISTINGS = "listings_clean.jsonl"
COMPLEXES = "complexes.jsonl"
OUT = "listings_valued.jsonl"
REPORT = "valuation_report.txt"

DISTRICTS = ["Есильский", "Нура", "Сарайшык", "Сарыарка", "Алматы", "Байконур"]
CLASSES = ["эконом", "комфорт", "бизнес", "элит"]


def featurize(l, complex_median, complexes):
    c = complexes.get(l.get("complex_slug") or "", {})
    floor = l.get("floor") or 0
    total = l.get("floors_total") or 0
    row = [
        l["area"],
        l["rooms"],
        floor,
        total,
        floor / total if total else 0.5,
        1 if floor == 1 else 0,
        1 if total and floor == total else 0,
        l.get("year_built") or 0,
        complex_median.get(l.get("complex_slug"), 0),  # target-encoding ЖК
    ]
    d = l.get("district")
    row += [1 if d == x else 0 for x in DISTRICTS]
    cls = (c.get("class") or "").lower()
    row += [1 if cls == x else 0 for x in CLASSES]
    return row


FEATURE_NAMES = (
    ["area", "rooms", "floor", "floors_total", "floor_ratio",
     "is_first_floor", "is_last_floor", "year_built", "complex_median_m2"]
    + [f"district_{d}" for d in DISTRICTS]
    + [f"class_{c}" for c in CLASSES]
)


def main():
    listings = [l for l in read_jsonl(LISTINGS) if not l.get("dup_suspect")]
    complexes = {c["slug"]: c for c in read_jsonl(COMPLEXES)}
    if len(listings) < 200:
        raise SystemExit(
            f"Всего {len(listings)} объявлений — мало для модели. "
            "Запустите полный скрейп; до тех пор приложение живёт на "
            "отклонении от медианы ЖК (это уже работает)."
        )

    # target-encoding: медиана ₸/м² по ЖК, посчитанная БЕЗ утечки — по трейну
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.metrics import mean_absolute_error, r2_score
    from sklearn.model_selection import train_test_split

    train, test = train_test_split(listings, test_size=0.2, random_state=42)

    by_slug = {}
    for l in train:
        s = l.get("complex_slug")
        if s:
            by_slug.setdefault(s, []).append(l["price_m2"])
    complex_median = {s: statistics.median(v) for s, v in by_slug.items()}
    global_median = statistics.median(l["price_m2"] for l in train)
    cm = lambda: {**{None: global_median}, **complex_median}

    X_tr = [featurize(l, complex_median, complexes) for l in train]
    y_tr = [l["price_m2"] for l in train]
    X_te = [featurize(l, complex_median, complexes) for l in test]
    y_te = [l["price_m2"] for l in test]

    model = GradientBoostingRegressor(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, random_state=42,
    )
    model.fit(X_tr, y_tr)
    pred = model.predict(X_te)

    mae = mean_absolute_error(y_te, pred)
    r2 = r2_score(y_te, pred)
    # наивный базлайн: медиана ЖК (или глобальная)
    naive = [complex_median.get(l.get("complex_slug"), global_median) for l in test]
    mae_naive = mean_absolute_error(y_te, naive)

    lines = [
        f"дата: {datetime.date.today().isoformat()}",
        f"обучение: {len(train)}, тест: {len(test)}",
        f"MAE модели:   {mae:,.0f} ₸/м²",
        f"MAE базлайна: {mae_naive:,.0f} ₸/м² (медиана ЖК)",
        f"R²: {r2:.3f}",
        "",
        "важность признаков:",
    ]
    imp = sorted(zip(FEATURE_NAMES, model.feature_importances_),
                 key=lambda x: -x[1])
    lines += [f"  {n:22s} {v:.3f}" for n, v in imp[:12]]

    use_model = mae < mae_naive
    lines.append("")
    lines.append("ВЕРДИКТ: " + (
        "модель бьёт базлайн — используем её." if use_model else
        "модель НЕ бьёт медиану ЖК — fair_value пишем по базлайну, "
        "модель в прод не идёт (честность дороже строчки в резюме)."))
    report = "\n".join(lines)
    open(REPORT, "w", encoding="utf-8").write(report)
    print(report)

    # fair_value для ВСЕХ объявлений
    all_listings = read_jsonl(LISTINGS)
    open(OUT, "w").close()
    for l in all_listings:
        if use_model:
            fair = float(model.predict([featurize(l, complex_median, complexes)])[0])
        else:
            fair = complex_median.get(l.get("complex_slug"), global_median)
        l["fair_m2"] = round(fair)
        l["deviation_pct"] = round((fair - l["price_m2"]) / fair * 100, 1)
        append_jsonl(OUT, l)
    print(f"\n{OUT}: {len(all_listings)} строк с fair_m2/deviation_pct")
    print("Дальше: заменить listings_clean на listings_valued в load_supabase.py"
          " (или просто переименовать файл).")


if __name__ == "__main__":
    main()
