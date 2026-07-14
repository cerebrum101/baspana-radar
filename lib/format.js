export const fmt = (n) =>
  n == null ? "—" : new Intl.NumberFormat("ru-RU").format(Math.round(n));

// deviation_pct = (fair - asked) / fair. Positive => cheaper than fair (good).
// Stored as a fraction or already as percent — normalise either way.
export const DEV_CAP = 35; // |отклонение| выше — ошибка модели, процент не показываем

// Модель ошибается на ~13% (MAE/медиана), поэтому показываем диапазон, а не точку.
export const FAIR_BAND = 0.13;
export function fairRange(m2) {
  if (!m2) return null;
  return [Math.round(m2 * (1 - FAIR_BAND)), Math.round(m2 * (1 + FAIR_BAND))];
}

export function devBadge(d) {
  if (d == null) return { cls: "b-neu", big: "нет оценки", sub: "" };
  let p = Math.abs(d) <= 1.5 ? d * 100 : d;
  p = Math.round(p);
  if (Math.abs(p) > DEV_CAP) return { cls: "b-neu", big: "оценка неточна", sub: "мало данных" };
  if (p >= 3) return { cls: "b-good", big: "−" + p + "%", sub: "ниже справедливой" };
  if (p <= -3) return { cls: "b-bad", big: "+" + Math.abs(p) + "%", sub: "выше справедливой" };
  return { cls: "b-neu", big: "≈ рынок", sub: "справедливая" };
}

export const SELLER = {
  owner: ["owner", "Хозяин"],
  specialist: ["", "Риелтор"],
  agent: ["", "Агент"],
  company: ["", "Компания"],
  developer: ["", "Застройщик"],
};

export const DISTRICTS = [
  "Есильский", "Алматы", "Сарыарка", "Байконур", "Нура", "Сарайшык",
];
