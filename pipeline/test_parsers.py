"""Unit tests for the spiders' parsers, using fixtures reconstructed from
real krisha.kz pages captured on 2026-07-12 (Времена года. Весна).
Run: python test_parsers.py
"""
import scrape_listings as sl
import scrape_complexes as sc

# --- fixture 1: listings search card (structure mirrors real выдача) ---
CARD_HTML = """
<html><body>
<div class="a-list">
  <div class="a-card">
    <a href="/a/show/1011516255"><img src="x.jpg"></a>
    <div class="a-card__inc">
      <a href="/a/show/1011516255">2-комнатная квартира · 66.2 м² · 4/14 этаж</a>
      <div class="a-card__price">39 000 000 ₸</div>
      <div class="a-card__subtitle">Есильский р-н, Кабанбай батыра 48а — Ботанический сад</div>
      <div class="a-card__text-preview">жил. комплекс Времена года. Весна, монолитный дом,
        2017 г.п., потолки 2.7м., санузел раздельный, меблирована полностью,
        Без комиссии для покупателя</div>
      <div><a href="https://krisha.kz/complex/show/vremena-goda-vesna/">ЖК «Времена года. Весна»</a></div>
      <div class="a-card__owner">Личность подтверждена Специалист</div>
    </div>
  </div>
  <div class="a-card">
    <a href="/a/show/1010732664">1-комнатная квартира · 37 м² · 1/14 этаж</a>
    <div>26 000 000 ₸</div>
    <div>Есильский р-н, Толе Би 28/1</div>
    <div>жил. комплекс Балауса, 2020 г.п., Срочно, торг. Хозяин недвижимости</div>
  </div>
</div>
</body></html>
"""

# --- fixture 2: complex page (lines from the real Весна page) ---
COMPLEX_HTML = """
<html><body>
<h1>ЖК Времена года. Весна в Астане</h1>
<p>Нет данных</p>
<p>Статус строительства</p><p>Строящийся</p>
<p>Срок сдачи</p><p>III квартал 2017 г.</p>
<p>Расположение</p><p>Астана, Есильский р-н, пр. Кабанбай батыра, 46, 46а, 46б – ул. Керей и Жанибек хандар</p>
<p>Застройщик</p><p>BI Group Юг</p>
<p>Разрешения</p><p>Нет документов на ЖК</p>
<p>Класс жилья</p><p>комфорт</p>
<p>Этажность</p><p>15 этажей</p>
<p>Высота потолков</p><p>2.7 м</p>
<p>Количество квартир</p><p>272</p>
<p>1 очередь: Разрешение на привлечение средств дольщиков № 17 от 13.10.2017 года,
Уполномоченная компания ТОО «Аманат Строй», застройщик – ТОО «KazIndustrialGroup»</p>
</body></html>
"""

PRICE_HTML = """<html><body><h1>ЖК Park City Forum в Астане</h1>
<p>от 526 000 〒 за м²</p><p>актуальная цена на 8 января</p>
<p>Класс жилья</p><p>комфорт</p></body></html>"""


def check(name, cond, got=None):
    print(f"  {'OK ' if cond else 'FAIL'} {name}" + ("" if cond else f"  → got: {got!r}"))
    return cond


print("=== parse_cards (listings) ===")
recs = sl.parse_cards(CARD_HTML)
ok = check("нашёл 2 карточки", len(recs) == 2, len(recs))
r = next((x for x in recs if x["id"] == "1011516255"), {})
ok &= check("id", r.get("id") == "1011516255", r.get("id"))
ok &= check("rooms=2", r.get("rooms") == 2, r.get("rooms"))
ok &= check("area=66.2", r.get("area") == 66.2, r.get("area"))
ok &= check("floor 4/14", (r.get("floor"), r.get("floors_total")) == (4, 14))
ok &= check("price=39000000", r.get("price") == 39000000, r.get("price"))
ok &= check("complex_slug", r.get("complex_slug") == "vremena-goda-vesna", r.get("complex_slug"))
ok &= check("complex_name_raw", r.get("complex_name_raw") == "Времена года. Весна", r.get("complex_name_raw"))
ok &= check("year=2017", r.get("year_built") == 2017, r.get("year_built"))
ok &= check("district", r.get("district") == "Есильский", r.get("district"))
ok &= check("seller=specialist", r.get("seller_type") == "specialist", r.get("seller_type"))
r2 = next((x for x in recs if x["id"] == "1010732664"), {})
ok &= check("2я карточка: urgent", r2.get("urgent") is True, r2.get("urgent"))
ok &= check("2я карточка: owner", r2.get("seller_type") == "owner", r2.get("seller_type"))
ok &= check("2я карточка: slug=None (нет ссылки)", r2.get("complex_slug") is None, r2.get("complex_slug"))

print("\n=== parse_complex (ЖК) ===")
rec = sc.parse_complex(COMPLEX_HTML, "vremena-goda-vesna", "u", "astana")
ok &= check("name", rec["name"] == "ЖК Времена года. Весна", rec["name"])
ok &= check("status", rec["status"] == "Строящийся", rec["status"])
ok &= check("deadline", rec["deadline_declared"] == "III квартал 2017 г.", rec["deadline_declared"])
ok &= check("class", rec["class"] == "комфорт", rec["class"])
ok &= check("developer_brand", rec["developer_brand"] == "BI Group Юг", rec["developer_brand"])
ok &= check("developer_legal", rec["developer_legal"] == "ТОО «KazIndustrialGroup»", rec["developer_legal"])
ok &= check("district", rec.get("district") == "Есильский", rec.get("district"))
ok &= check("ceiling_m=2.7", rec.get("ceiling_m") == 2.7, rec.get("ceiling_m"))
ok &= check("apartments=272", rec.get("apartments_total") == 272, rec.get("apartments_total"))
ok &= check("permits", rec["permits"] == "Нет документов на ЖК", rec["permits"])

rec2 = sc.parse_complex(PRICE_HTML, "parkcityforum", "u", "astana")
ok &= check("price_m2=526000", rec2.get("price_m2_listed") == 526000, rec2.get("price_m2_listed"))
ok &= check("price date", rec2.get("price_m2_date") == "8 января", rec2.get("price_m2_date"))

print("\n" + ("ALL TESTS PASSED" if ok else "SOME TESTS FAILED"))
raise SystemExit(0 if ok else 1)
