// Transparent scoring engine. Работает на предзагруженном контексте
// (getContext() из data.js) — ноль запросов внутри цикла.
const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));

const WEIGHTS = {
  live: { value: 0.35, fit: 0.45, risk: 0.2 },
  invest: { value: 0.5, fit: 0.3, risk: 0.2 },
};

// riskTolerance: 0 = осторожный, 0.5 = сбалансированный, 1 = толерантный
export function scoreListing(listing, prefs, ctx) {
  const stats = ctx.statsBySlug[listing.complexSlug] || null;
  const card = ctx.cardsBySlug[listing.complexSlug] || null;
  const complex = ctx.complexesBySlug[listing.complexSlug] || null;
  const w = WEIGHTS[prefs.purpose] || WEIGHTS.live;

  // --- выгода: отклонение ₸/м² объявления от медианы своего ЖК ---
  const m2 = listing.price / listing.area;
  let valueScore = 50;
  let deviationPct = null;
  if (stats && stats.medianM2 && !stats.lowSample) {
    deviationPct = ((stats.medianM2 - m2) / stats.medianM2) * 100; // + = ниже рынка
    valueScore = clamp(50 + deviationPct * 2.5, 0, 100);
  }

  // --- соответствие: бюджет и район ---
  let fitScore = 100;
  if (prefs.budget && listing.price > prefs.budget) {
    fitScore -= clamp((listing.price / prefs.budget - 1) * 200, 0, 60);
  }
  if (prefs.district && prefs.district !== "any") {
    if (complex && complex.district !== prefs.district) fitScore -= 30;
  }
  fitScore = clamp(fitScore, 0, 100);

  // --- риск: из карточки ЖК, масштабируется толерантностью ---
  const baseRisk = card ? card.riskScore : 30; // ЖК без карточки = нейтрально
  const riskPenalty = baseRisk * (1 - (prefs.riskTolerance ?? 0.5));

  const total = w.value * valueScore + w.fit * fitScore - w.risk * riskPenalty;

  return {
    total: Math.round(clamp(total, 0, 100)),
    breakdown: {
      valueScore: Math.round(valueScore),
      deviationPct: deviationPct === null ? null : Math.round(deviationPct),
      fitScore: Math.round(fitScore),
      riskPenalty: Math.round(riskPenalty),
      baseRisk,
      hasCard: !!card,
      lowSample: stats ? stats.lowSample : true,
      weights: w,
      m2: Math.round(m2),
      medianM2: stats && stats.medianM2 ? Math.round(stats.medianM2) : null,
    },
  };
}

export function rankListings(listings, prefs, ctx) {
  return listings
    .filter((l) => !prefs.budget || l.price <= prefs.budget * 1.15)
    .map((l) => ({ listing: l, score: scoreListing(l, prefs, ctx) }))
    .sort((a, b) => b.score.total - a.score.total);
}
