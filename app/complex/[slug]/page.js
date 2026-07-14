import Link from "next/link";
import { notFound } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { fmt } from "@/lib/format";
import ListingCard from "../../components/ListingCard";

export const revalidate = 300;

export async function generateMetadata({ params }) {
  const { data: c } = await supabase
    .from("complexes")
    .select("name, district, class, status")
    .eq("slug", params.slug)
    .maybeSingle();
  if (!c) return { title: "ЖК не найден | Baspana Radar" };
  const bits = [c.class, c.status, c.district].filter(Boolean).join(", ");
  return {
    title: `ЖК ${c.name} в Астане — цены, статистика, риск | Baspana Radar`,
    description: `${c.name}${bits ? " (" + bits + ")" : ""}: справедливые цены ₸/м², статистика объявлений и оценка риска по данным krisha.kz.`,
  };
}

const TIER_LABEL = { confirmed: "подтверждено", no_data: "нет данных" };

export default async function ComplexPage({ params }) {
  const slug = params.slug;
  const [{ data: c }, { data: s }, { data: card }, { data: listings }] = await Promise.all([
    supabase.from("complexes").select("*").eq("slug", slug).maybeSingle(),
    supabase.from("complex_stats").select("*").eq("complex_slug", slug).maybeSingle(),
    supabase.from("dd_cards").select("*").eq("complex_slug", slug).maybeSingle(),
    supabase.from("listings").select("*").eq("complex_slug", slug).eq("dup_suspect", false)
      .order("deviation_pct", { ascending: false, nullsFirst: false }).limit(24),
  ]);

  if (!c) notFound();

  const sub = [c.class, c.status, c.developer_brand || c.developer_legal].filter(Boolean).join(" · ");
  const rc = card ? (card.risk_score <= 30 ? "var(--good)" : card.risk_score <= 55 ? "#b45309" : "var(--bad)") : null;

  return (
    <main className="wrap">
      <Link className="back" href="/">← ко всем объявлениям</Link>

      <div className="cx-head">
        <div>
          <h1 className="cx-title">{c.name}</h1>
          <div className="cx-sub">
            {sub || "Астана"}{c.deadline_declared ? ` · сдача ${c.deadline_declared}` : ""}
          </div>
        </div>
      </div>

      {s && (
        <div className="panel">
          <div className="sec-t">Цены по объявлениям</div>
          <div className="kpis">
            <div className="kpi"><b>{fmt(s.median_m2)}</b><span>медиана ₸/м²</span></div>
            <div className="kpi"><b>{fmt(s.p25_m2)}–{fmt(s.p75_m2)}</b><span>разброс ₸/м²</span></div>
            <div className="kpi"><b>{s.n_listings}</b><span>объявлений{s.low_sample ? " · мало данных" : ""}</span></div>
          </div>
        </div>
      )}

      <div className="panel">
        <div className="sec-t">Оценка риска</div>
        {card ? (
          <>
            <div className="risk">
              <div className="gauge" style={{ "--v": card.risk_score, "--rc": rc }}>
                <i>{card.risk_score}</i>
              </div>
              <div className="verdict">{card.verdict}</div>
            </div>
            {card.strengths?.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <div className="sec-t">Плюсы</div>
                <ul className="pts">{card.strengths.map((x, i) => <li key={i}>{x}</li>)}</ul>
              </div>
            )}
            {card.weaknesses?.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <div className="sec-t">Минусы</div>
                <ul className="pts">{card.weaknesses.map((x, i) => <li key={i}>{x}</li>)}</ul>
              </div>
            )}
            {card.flags?.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <div className="sec-t">Флаги</div>
                {card.flags.map((f, i) => (
                  <div className="flag" key={i}>
                    <div className="t">
                      <span className={`tier ${f.tier}`}>{TIER_LABEL[f.tier] || f.tier}</span>
                      {f.title}
                    </div>
                    {f.detail && <div className="d">{f.detail}</div>}
                  </div>
                ))}
              </div>
            )}
          </>
        ) : (
          <div className="note">Карточка due-diligence для этого ЖК ещё не сгенерирована. Ценовая статистика выше доступна.</div>
        )}
        <div className="disclaim">
          Источник: krisha.kz + снапшот Baspana Radar. Репутация застройщика и отзывы жильцов не проверялись.
          {c.krisha_url && (
            <> <a href={c.krisha_url} target="_blank" rel="noopener noreferrer">Страница ЖК на krisha →</a></>
          )}
        </div>
      </div>

      {listings?.length > 0 && (
        <>
          <div className="sec-t" style={{ marginTop: 8 }}>Объявления в этом ЖК</div>
          <div className="grid">
            {listings.map((l) => <ListingCard key={l.id} l={l} />)}
          </div>
        </>
      )}
    </main>
  );
}
