-- Baspana Radar · T2 Block 0
-- Paste into Supabase SQL Editor and run once.

create table if not exists complexes (
  slug              text primary key,
  name              text not null,
  city              text default 'astana',
  district          text,
  class             text,
  developer_brand   text,
  developer_legal   text,
  status            text,              -- сдан / строится (по krisha)
  deadline_declared text,              -- заявленный срок сдачи (сырой текст)
  floors            text,
  ceiling_m         numeric,
  apartments_total  int,
  price_m2_listed   numeric,           -- "от X ₸ за м²" на странице ЖК
  price_m2_date     text,              -- "актуальная цена на ..."
  permits           text,              -- есть/нет документов (по krisha)
  address           text,
  krisha_url        text,
  scraped_at        timestamptz default now()
);

create table if not exists listings (
  id                text primary key,  -- krisha advert id
  complex_slug      text references complexes(slug),
  complex_name_raw  text,              -- как написано в объявлении
  rooms             int,
  area              numeric,
  floor             int,
  floors_total      int,
  price             bigint,
  price_m2          numeric,
  year_built        int,
  condition         text,
  address           text,
  district          text,
  seller_type       text,              -- owner / agent / specialist / company (БЕЗ имён)
  urgent            boolean default false,
  dup_suspect       boolean default false,
  url               text,
  first_seen        date default current_date,
  last_seen         date default current_date,
  raw_snippet       text               -- фрагмент описания для карточек Layer 1
);

create index if not exists listings_complex_idx on listings (complex_slug);
create index if not exists listings_rooms_idx   on listings (rooms);

create table if not exists complex_stats (
  complex_slug  text primary key references complexes(slug),
  snapshot_date date,
  n_listings    int,
  median_m2     numeric,
  p25_m2        numeric,
  p75_m2        numeric,
  min_price     bigint,
  max_price     bigint,
  low_sample    boolean,               -- n < 8: статистике не доверять
  anomaly_flags jsonb default '[]',    -- [{code, detail}, ...]
  computed_at   timestamptz default now()
);

create table if not exists dd_cards (
  complex_slug text primary key references complexes(slug),
  layer        int,                    -- 1 = только свои данные, 2 = внешние источники
  risk_score   int,                    -- 0..100
  verdict      text,
  strengths    jsonb,
  weaknesses   jsonb,
  flags        jsonb,                  -- [{tier, title, detail, source}] tier: confirmed|reported|rumor|no_data
  sources      jsonb,
  generated_at date,
  model        text                    -- какая LLM сгенерировала (для воспроизводимости)
);

create table if not exists scrape_runs (
  id          bigint generated always as identity primary key,
  kind        text,                    -- complexes | listings
  started_at  timestamptz,
  finished_at timestamptz,
  pages       int,
  items       int,
  notes       text
);

-- Публичное чтение, запись только сервисным ключом (загрузчик).
alter table complexes     enable row level security;
alter table listings      enable row level security;
alter table complex_stats enable row level security;
alter table dd_cards      enable row level security;
alter table scrape_runs   enable row level security;

create policy "public read complexes"     on complexes     for select using (true);
create policy "public read listings"      on listings      for select using (true);
create policy "public read complex_stats" on complex_stats for select using (true);
create policy "public read dd_cards"      on dd_cards      for select using (true);
