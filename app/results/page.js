import Link from "next/link";
import { getContext, getListings } from "../../lib/data";
import { rankListings } from "../../lib/scoring";

export const revalidate = 3600;

const fmtMln = (p) => `${(p / 1e6).toLocaleString("ru-RU", { maximumFractionDigits: 1 })} млн ₸`;
const fmtK = (p) => `${Math.round(p / 1000)} тыс ₸/м²`;

export const metadata = { title: "Подбор квартир — Baspana Radar" };

export default async function Results({ searchParams }) {
  const prefs = {
    budget: searchParams.budget ? Number(searchParams.budget) * 1e6 : null,
    rooms: searchParams.rooms ? Number(searchParams.rooms) : null,
    district: searchParams.district || "any",
    purpose: searchParams.purpose === "invest" ? "invest" : "live",
    riskTolerance: searchParams.risk !== undefined ? Number(searchParams.risk) : 0.5,
  };

  const [listings, ctx] = await Promise.all([
    getListings({ rooms: prefs.rooms }),
    getContext(),
  ]);
  const ranked = rankListings(listings, prefs, ctx).slice(0, 10);

  return (
    <main>
      <h1>Подбор под ваши приоритеты</h1>
      <p className="sub">
        {prefs.rooms}-комн · до {prefs.budget ? fmtMln(prefs.budget * 1.15) : "без лимита"} (бюджет +15% на торг) ·{" "}
        {prefs.purpose === "invest" ? "инвестиция" : "для жизни"} ·{" "}
        <Link href="/">изменить условия</Link>
      </p>

      {ranked.length === 0 && (
        <div className="card">
          Ничего не нашлось под эти условия в текущем срезе данных. Попробуйте
          увеличить бюджет или сменить район.
        </div>
      )}

      {ranked.map(({ listing, score }, i) => {
        const complex = ctx.complexesBySlug[listing.complexSlug] || null;
        const b = score.breakdown;
        return (
          <div className="card" key={listing.id}>
            <div className="listing-head">
              <div>
                <div className="listing-title">
                  {i + 1}. {listing.rooms}-комн · {listing.area} м² · {listing.floorLabel} эт
                  {listing.demo && <> {" "}<span className="tag demo">demo-данные</span></>}
                  {listing.dupSuspect && <> {" "}<span className="tag reported">возможный дубль</span></>}
                  {listing.urgent && <> {" "}<span className="tag good">срочно / торг</span></>}
                </div>
                <div className="meta">
                  <Link href={`/zhk/${listing.complexSlug}`}>{complex?.name}</Link>
                  {" · "}{complex?.district} р-н · {listing.address} · {listing.condition}
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div className="price">{fmtMln(listing.price)}</div>
                <div className="score-pill" title="Итоговый балл 0–100">{score.total}</div>
              </div>
            </div>
            <div className="breakdown">
              <span>
                Цена: <b>{fmtK(b.m2)}</b>
                {b.deviationPct !== null && (
                  <>
                    {" "}({b.deviationPct > 0 ? "−" : "+"}
                    {Math.abs(b.deviationPct)}% к медиане ЖК {fmtK(b.medianM2)})
                  </>
                )}
                {b.lowSample && " (мало данных по ЖК)"}
              </span>
              <span>Выгода: <b>{b.valueScore}</b>/100</span>
              <span>Соответствие: <b>{b.fitScore}</b>/100</span>
              <span>
                Штраф за риск: <b>−{b.riskPenalty}</b>
                {!b.hasCard && " (ЖК без карточки — нейтрально)"}
              </span>
              {listing.url && (
                <a href={listing.url} target="_blank" rel="noopener noreferrer">
                  объявление на krisha ↗
                </a>
              )}
            </div>
          </div>
        );
      })}

      <p className="disclaimer">
        Балл = {`{выгода}`}·w₁ + {`{соответствие}`}·w₂ − {`{риск ЖК}`}·w₃, веса
        зависят от цели покупки, штраф за риск — от вашей толерантности.
        Формула открыта: lib/scoring.js. Demo-срез, цены могли измениться.
      </p>
    </main>
  );
}
