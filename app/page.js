import Link from "next/link";
import { supabase } from "@/lib/supabase";
import { DEV_CAP } from "@/lib/format";
import Filters from "./components/Filters";
import ListingCard from "./components/ListingCard";

export const revalidate = 300; // ISR: refresh at most every 5 min

const PER = 48;

export default async function Home({ searchParams }) {
  const { district, rooms, maxPrice, sort } = searchParams;
  const page = Math.max(1, parseInt(searchParams.page || "1", 10));
  const from = (page - 1) * PER;
  const to = from + PER - 1;

  let q = supabase
    .from("listings")
    .select("*", { count: "exact" })
    .eq("dup_suspect", false)
    .range(from, to);

  if (district) q = q.eq("district", district);
  if (rooms) q = rooms === "5" ? q.gte("rooms", 5) : q.eq("rooms", Number(rooms));
  if (maxPrice) q = q.lte("price", Number(maxPrice));

  const sortKey = sort || "deviation_pct.desc";
  // При сортировке по цене-к-рынку убираем неправдоподобные оценки модели,
  // чтобы вверху не висел мусор вроде «−71%».
  if (sortKey.startsWith("deviation_pct")) {
    q = q.gte("deviation_pct", -DEV_CAP).lte("deviation_pct", DEV_CAP);
  }
  const [col, dir] = sortKey.split(".");
  q = q.order(col, { ascending: dir === "asc", nullsFirst: false });

  const { data: rows, error, count } = await q;

  const total = count || 0;
  const pages = Math.ceil(total / PER);
  const pageUrl = (p) => {
    const sp = new URLSearchParams();
    if (district) sp.set("district", district);
    if (rooms) sp.set("rooms", rooms);
    if (maxPrice) sp.set("maxPrice", maxPrice);
    if (sort) sp.set("sort", sort);
    sp.set("page", String(p));
    return "/?" + sp.toString();
  };

  return (
    <>
      <Filters />
      <main className="wrap">
        <div className="meta-row">
          <div className="count">
            {error
              ? "Ошибка загрузки"
              : total
              ? <>{fmtInt(total)} объявлений <span>· стр. {page} из {pages}</span></>
              : "Ничего не найдено"}
          </div>
          <div className="note">Справедливая цена — оценка модели по 26 000+ объявлений. Не оффер.</div>
        </div>

        {error && <div className="empty">Не удалось получить данные: {error.message}</div>}

        {!error && total === 0 && (
          <div className="empty">Под фильтры ничего не подошло. Ослабьте условия.</div>
        )}

        <div className="grid">
          {rows?.map((l) => <ListingCard key={l.id} l={l} />)}
        </div>

        {pages > 1 && (
          <nav className="pager">
            {page > 1 && <Link className="btn ghost" href={pageUrl(page - 1)}>← Назад</Link>}
            <span className="pager-info">{page} / {pages}</span>
            {page < pages && <Link className="btn" href={pageUrl(page + 1)}>Вперёд →</Link>}
          </nav>
        )}
      </main>
    </>
  );
}

const fmtInt = (n) => new Intl.NumberFormat("ru-RU").format(n);
