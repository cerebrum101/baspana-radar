// Data layer, dual-mode:
//  - env NEXT_PUBLIC_SUPABASE_URL + NEXT_PUBLIC_SUPABASE_ANON_KEY заданы →
//    читаем Supabase (реальный снапшот из pipeline);
//  - env нет → статический JSON-срез из data/ (demo-режим).
// Все функции async; страницы получают одинаковые формы объектов в обоих
// режимах — маппинг снэйк-кейса БД в кэмел происходит здесь и только здесь.
import complexesJson from "../data/complexes.json";
import listingsJson from "../data/listings.json";
import cardsJson from "../data/cards.json";

export const SNAPSHOT_DATE = "2026-07-12";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
const USE_DB = Boolean(url && key);

let _sb = null;
async function sb() {
  if (!_sb) {
    const { createClient } = await import("@supabase/supabase-js");
    _sb = createClient(url, key);
  }
  return _sb;
}

// ---------- мапперы БД → форма приложения ----------
const mapComplex = (c) => ({
  slug: c.slug,
  name: c.name,
  district: c.district,
  class: c.class,
  developerBrand: c.developer_brand,
  developerLegal: c.developer_legal,
  built: c.deadline_declared || "н/д",
  floors: c.floors,
  status: c.status,
  address: c.address,
  krishaUrl: c.krisha_url,
});

const mapListing = (l) => ({
  id: l.id,
  complexSlug: l.complex_slug,
  rooms: l.rooms,
  area: Number(l.area),
  floorLabel:
    l.floor && l.floors_total ? `${l.floor}/${l.floors_total}` : "н/д",
  price: Number(l.price),
  year: l.year_built,
  condition: l.condition,
  address: l.address,
  url: l.url,
  urgent: l.urgent,
  dupSuspect: l.dup_suspect,
  demo: false,
});

const mapStats = (s) => ({
  count: s.n_listings,
  medianM2: Number(s.median_m2),
  minPrice: Number(s.min_price),
  maxPrice: Number(s.max_price),
  lowSample: s.low_sample,
  anomalyFlags: s.anomaly_flags || [],
});

const mapCard = (c) => ({
  layer: c.layer,
  generatedAt: c.generated_at,
  riskScore: c.risk_score,
  verdict: c.verdict,
  strengths: c.strengths || [],
  weaknesses: c.weaknesses || [],
  flags: c.flags || [],
  sources: c.sources || [],
});

// ---------- JSON-режим ----------
const jsonListing = (l) => ({
  ...l,
  complexSlug: l.complexSlug,
  floorLabel: l.floor,
  year: l.year,
});

function median(nums) {
  if (!nums.length) return null;
  const s = [...nums].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

function jsonStats(slug) {
  const ls = listingsJson.filter((l) => l.complexSlug === slug);
  if (!ls.length) return null;
  const perM2 = ls.map((l) => l.price / l.area);
  return {
    count: ls.length,
    medianM2: median(perM2),
    minPrice: Math.min(...ls.map((l) => l.price)),
    maxPrice: Math.max(...ls.map((l) => l.price)),
    lowSample: ls.length < 8,
    anomalyFlags: [],
  };
}

// ---------- публичный API ----------
export async function getComplexes() {
  if (!USE_DB) return complexesJson;
  const { data } = await (await sb()).from("complexes").select("*");
  return (data || []).map(mapComplex);
}

export async function getComplex(slug) {
  if (!USE_DB) return complexesJson.find((c) => c.slug === slug) || null;
  const { data } = await (await sb())
    .from("complexes").select("*").eq("slug", slug).maybeSingle();
  return data ? mapComplex(data) : null;
}

export async function getListings(filter = {}) {
  if (!USE_DB) {
    return listingsJson
      .filter((l) => !filter.complexSlug || l.complexSlug === filter.complexSlug)
      .filter((l) => !filter.rooms || l.rooms === Number(filter.rooms))
      .map(jsonListing);
  }
  let q = (await sb()).from("listings").select("*").limit(2000);
  if (filter.complexSlug) q = q.eq("complex_slug", filter.complexSlug);
  if (filter.rooms) q = q.eq("rooms", Number(filter.rooms));
  const { data } = await q;
  return (data || []).map(mapListing);
}

export async function getComplexStats(slug) {
  if (!USE_DB) return jsonStats(slug);
  const { data } = await (await sb())
    .from("complex_stats").select("*").eq("complex_slug", slug).maybeSingle();
  return data ? mapStats(data) : null;
}

export async function getCard(slug) {
  if (!USE_DB) return cardsJson[slug] || null;
  const { data } = await (await sb())
    .from("dd_cards").select("*").eq("complex_slug", slug).maybeSingle();
  return data ? mapCard(data) : null;
}

// Контекст для скоринга: все нужные справочники одним заходом,
// чтобы не делать N запросов на N объявлений.
export async function getContext() {
  if (!USE_DB) {
    const statsBySlug = {};
    for (const c of complexesJson) statsBySlug[c.slug] = jsonStats(c.slug);
    const complexesBySlug = Object.fromEntries(
      complexesJson.map((c) => [c.slug, c])
    );
    return { statsBySlug, cardsBySlug: cardsJson, complexesBySlug };
  }
  const client = await sb();
  const [stats, cards, complexes] = await Promise.all([
    client.from("complex_stats").select("*"),
    client.from("dd_cards").select("*"),
    client.from("complexes").select("*"),
  ]);
  return {
    statsBySlug: Object.fromEntries(
      (stats.data || []).map((s) => [s.complex_slug, mapStats(s)])
    ),
    cardsBySlug: Object.fromEntries(
      (cards.data || []).map((c) => [c.complex_slug, mapCard(c)])
    ),
    complexesBySlug: Object.fromEntries(
      (complexes.data || []).map((c) => [c.slug, mapComplex(c)])
    ),
  };
}
