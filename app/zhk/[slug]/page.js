import Link from "next/link";
import { notFound } from "next/navigation";
import { getCard, getComplex, getComplexes, getComplexStats, getListings } from "../../../lib/data";

const fmtMln = (p) => `${(p / 1e6).toLocaleString("ru-RU", { maximumFractionDigits: 1 })} млн ₸`;
const fmtK = (p) => `${Math.round(p / 1000)} тыс ₸/м²`;

const TIER_LABELS = {
  confirmed: "подтверждено",
  reported: "сообщается",
  rumor: "слух",
  no_data: "нет данных",
};

export const revalidate = 3600;
export const dynamicParams = true;

export async function generateStaticParams() {
  const complexes = await getComplexes();
  return complexes.slice(0, 50).map((c) => ({ slug: c.slug }));
}

export default async function ComplexPage({ params }) {
  const complex = await getComplex(params.slug);
  if (!complex) notFound();
  const [stats, card, listings] = await Promise.all([
    getComplexStats(params.slug),
    getCard(params.slug),
    getListings({ complexSlug: params.slug }),
  ]);

  return (
    <main>
      <h1>{complex.name}</h1>
      <p className="sub">
        {complex.district} р-н · {complex.address} ·{" "}
        <a href={complex.krishaUrl} target="_blank" rel="noopener noreferrer">страница на krisha ↗</a>
      </p>

      <div className="card">
        <table className="stats">
          <tbody>
            <tr><td>Класс</td><td>{complex.class}</td></tr>
            <tr><td>Застройщик (бренд)</td><td>{complex.developerBrand}</td></tr>
            <tr><td>Застройщик (юрлицо)</td><td>{complex.developerLegal}</td></tr>
            <tr><td>Годы постройки</td><td>{complex.built}</td></tr>
            <tr><td>Этажность</td><td>{complex.floors}</td></tr>
            <tr><td>Статус</td><td>{complex.status}</td></tr>
            {stats && (
              <>
                <tr><td>Объявлений в срезе</td><td>{stats.count}{stats.lowSample && " (мало для статистики)"}</td></tr>
                <tr><td>Медиана цены</td><td>{fmtK(stats.medianM2)}</td></tr>
                <tr><td>Диапазон цен</td><td>{fmtMln(stats.minPrice)} — {fmtMln(stats.maxPrice)}</td></tr>
              </>
            )}
          </tbody>
        </table>
        {stats && stats.anomalyFlags && stats.anomalyFlags.length > 0 && (
          <div style={{ marginTop: 10 }}>
            {stats.anomalyFlags.map((f, i) => (
              <div className="flag reported" key={i}>
                <div className="t">
                  <span className="tag reported">аномалия</span> {f.code}
                </div>
                <div className="d">{f.detail}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {card ? (
        <>
          <h2>Карточка due diligence <span className="tag no_data">слой {card.layer} · {card.generatedAt}</span></h2>
          <div className="verdict">{card.verdict}</div>

          <h2>Сильные стороны</h2>
          <ul className="plain">
            {card.strengths.map((s, i) => <li key={i}>{s}</li>)}
          </ul>

          <h2>Слабые стороны</h2>
          <ul className="plain">
            {card.weaknesses.map((s, i) => <li key={i}>{s}</li>)}
          </ul>

          <h2>Флаги рисков</h2>
          {card.flags.map((f, i) => (
            <div className={`flag ${f.tier}`} key={i}>
              <div className="t">
                <span className={`tag ${f.tier}`}>{TIER_LABELS[f.tier]}</span> {f.title}
              </div>
              <div className="d">{f.detail}</div>
              {f.source && (
                <div className="s">
                  <a href={f.source.url} target="_blank" rel="noopener noreferrer">
                    источник: {f.source.title} ↗
                  </a>
                </div>
              )}
            </div>
          ))}

          <h2>Источники</h2>
          <ul className="plain">
            {card.sources.map((s, i) => (
              <li key={i}>
                <a href={s.url} target="_blank" rel="noopener noreferrer">{s.title}</a>
              </li>
            ))}
          </ul>
        </>
      ) : (
        <div className="card">
          <b>Карточка due diligence ещё не сгенерирована.</b>
          <p className="meta" style={{ marginTop: 6 }}>
            Для этого ЖК пока есть только рыночная статистика. В полной версии
            карточка генерируется по запросу за ~90 секунд и кэшируется. Правило
            системы: ни одно утверждение без источника не поднимается выше
            уровня «слух»; при пустом корпусе данных карточка честно сообщает
            «нет данных», а не выдумывает.
          </p>
        </div>
      )}

      <h2>Объявления в этом ЖК ({listings.length})</h2>
      {listings.map((l) => (
        <div className="card" key={l.id}>
          <div className="listing-head">
            <div>
              <div className="listing-title">
                {l.rooms}-комн · {l.area} м² · {l.floorLabel} эт
                {l.demo && <> {" "}<span className="tag demo">demo-данные</span></>}
                {l.dupSuspect && <> {" "}<span className="tag reported">возможный дубль</span></>}
              </div>
              <div className="meta">{l.address} · {l.condition} · {l.year} г.п.</div>
            </div>
            <div className="price">{fmtMln(l.price)}</div>
          </div>
        </div>
      ))}

      <p className="disclaimer">
        <Link href="/">← к подбору</Link> · Не является финансовой или
        юридической консультацией. Проверяйте документы перед сделкой.
      </p>
    </main>
  );
}
