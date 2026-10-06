export function formatPct(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "0%";
  const rounded = Math.round(n * 10) / 10;
  const text = new Intl.NumberFormat("es-AR", {
    minimumFractionDigits: Number.isInteger(rounded) ? 0 : 1,
    maximumFractionDigits: 1,
  }).format(rounded);
  return `${text}%`;
}

export function reelTitle(caption) {
  const line = String(caption || "")
    .split("\n")
    .map((part) => part.trim())
    .find(Boolean);
  const title = line || "Reel sin título";
  return title.length > 90 ? `${title.slice(0, 89)}…` : title;
}

export function bioSnippet(bio) {
  const text = String(bio || "").replace(/\s+/g, " ").trim();
  if (!text) return "Sin bio";
  return text.length > 110 ? `${text.slice(0, 109)}…` : text;
}

export function initialOf(username) {
  const letter = String(username || "").replace(/^@/, "").trim().charAt(0);
  return (letter || "?").toUpperCase();
}

export const AVATAR_LABEL = {
  infoproductor: "Infoproductor",
  growth_operator: "Growth operator",
  otro: "Otro",
  sin_datos: "Sin datos",
};
