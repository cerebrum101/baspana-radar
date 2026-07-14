import { supabase } from "@/lib/supabase";
import Filters from "./components/Filters";
import ListingCard from "./components/ListingCard";

export const revalidate = 300; // ISR: refresh at most every 5 min

const PAGE = 60;

export default async function Home({ searchParams }) {
  const { district, rooms, maxPrice, sort } = searchParams;

  let q = supabase.from("listings").select("*").eq("dup_suspect", false).limit(PAGE);
  if (district) q = q.eq("district", district);
  if (rooms) q = rooms === "5" ? q.gte("rooms", 5) : q.eq("rooms", Number(rooms));
  if (maxPrice) q = q.lte("price", Number(maxPrice));

  const [col, dir] = (sort || "deviation_pct.desc").split(".");
  q = q.order(col, { ascending: dir === "asc", nullsFirst: false });

  const { data: rows, error } = await q;

  return (
    <>
      <Filters />
      <main className="wrap">
        <div className="meta-row">
          <div className="count">
            {error
              ? "Ошибка загрузки"
              : rows?.length
              ? <>{rows.length === PAGE ? `${PAGE}+` : rows.length} объявлений <span>· отобраны по фильтрам</span></>
              : "Ничего не найдено"}
          </div>
          <div className="note">Справедливая цена — оценка модели по 26 000+ объявлений. Не оффер.</div>
        </div>

        {error && <div className="empty">Не удалось получить данные: {error.message}</div>}

        {!error && rows?.length === 0 && (
          <div className="empty">Под фильтры ничего не подошло. Ослабьте условия.</div>
        )}

        <div className="grid">
          {rows?.map((l) => <ListingCard key={l.id} l={l} />)}
        </div>
      </main>
    </>
  );
}
