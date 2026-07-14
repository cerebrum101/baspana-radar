"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { DISTRICTS } from "@/lib/format";

const SORTS = [
  ["deviation_pct.desc", "Лучшая цена к рынку"],
  ["price.asc", "Сначала дешёвые"],
  ["price.desc", "Сначала дорогие"],
  ["area.desc", "Больше площадь"],
];

export default function Filters() {
  const router = useRouter();
  const sp = useSearchParams();
  const get = (k) => sp.get(k) || "";

  function apply(patch) {
    const p = new URLSearchParams(sp.toString());
    for (const [k, v] of Object.entries(patch)) {
      if (v) p.set(k, v);
      else p.delete(k);
    }
    router.push("/?" + p.toString());
  }

  return (
    <div className="filters">
      <div className="wrap fbar">
        <div className="field">
          <label>Район</label>
          <select value={get("district")} onChange={(e) => apply({ district: e.target.value })}>
            <option value="">Все районы</option>
            {DISTRICTS.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Комнат</label>
          <select value={get("rooms")} onChange={(e) => apply({ rooms: e.target.value })}>
            <option value="">Любое</option>
            {["1", "2", "3", "4", "5"].map((r) => (
              <option key={r} value={r}>{r === "5" ? "5+" : r}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Цена до, ₸</label>
          <input
            type="number"
            min="0"
            step="1000000"
            placeholder="напр. 30000000"
            defaultValue={get("maxPrice")}
            onKeyDown={(e) => e.key === "Enter" && apply({ maxPrice: e.target.value })}
            onBlur={(e) => apply({ maxPrice: e.target.value })}
          />
        </div>
        <div className="field">
          <label>Сортировка</label>
          <select value={get("sort") || "deviation_pct.desc"} onChange={(e) => apply({ sort: e.target.value })}>
            {SORTS.map(([v, t]) => (
              <option key={v} value={v}>{t}</option>
            ))}
          </select>
        </div>
        <button className="btn ghost" onClick={() => router.push("/")}>Сброс</button>
      </div>
    </div>
  );
}
