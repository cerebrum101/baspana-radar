import Link from "next/link";
import { fmt, devBadge, fairRange, SELLER } from "@/lib/format";

export default function ListingCard({ l }) {
  const b = devBadge(l.deviation_pct);
  const floor = l.floor ? `${l.floor}${l.floors_total ? "/" + l.floors_total : ""} эт.` : "";
  const spec = [`${l.rooms}-комн`, `${l.area} м²`, floor].filter(Boolean).join(" · ");
  const seller = SELLER[l.seller_type];
  const href = l.complex_slug ? `/complex/${l.complex_slug}` : null;
  const range = fairRange(l.fair_m2);

  const inner = (
    <div className="card">
      <div className={`badge ${b.cls}`}>{b.big}<small>{b.sub}</small></div>
      <div className="price">
        {l.price_from && <span className="from">от </span>}
        {fmt(l.price)} ₸
      </div>
      <div className="spec">{spec}</div>
      <div className="cx">{l.complex_name_raw || l.address || "Вторичное жильё"}</div>
      <div className="loc">
        {l.district || ""}{l.year_built ? ` · ${l.year_built} г.` : ""}
      </div>
      <div className="chips">
        {seller && <span className={`chip ${seller[0]}`}>{seller[1]}</span>}
        {l.urgent && <span className="chip urgent">Срочно</span>}
      </div>
      <div className="fair">
        {range
          ? `Справедливо ≈ ${fmt(range[0])}–${fmt(range[1])} ₸/м²`
          : "Оценка недоступна"}
        {` · в объявлении ${fmt(l.price_m2)} ₸/м²`}
      </div>
    </div>
  );

  return href ? <Link href={href}>{inner}</Link> : inner;
}
