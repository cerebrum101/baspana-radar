export const fmt = (n) =>
  n == null ? "—" : new Intl.NumberFormat("ru-RU").format(Math.round(n));

// deviation_pct = (fair - asked) / fair. Positive => cheaper than fair (good).
// Stored as a fraction or already as percent — normalise either way.
export function devBadge(d) {
  if (d == null) return { cls: "b-neu", big: "нет оценки", sub: "" };
  let p = Math.abs(d) <= 1.5 ? d * 100 : d;
  p = Math.round(p);
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
