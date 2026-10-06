export class AuthError extends Error {
  constructor() {
    super("auth");
    this.code = 401;
  }
}

async function request(path) {
  const response = await fetch(path, {
    credentials: "include",
    headers: { Accept: "application/json" },
  });
  if (response.status === 401) throw new AuthError();
  if (!response.ok) throw new Error("request");
  return response.json();
}

export function getReels() {
  return request("/api/reels");
}

export function getCalificados(reelId, { limit = 50, offset = 0 } = {}) {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  return request(`/api/reels/${reelId}/calificados?${params.toString()}`);
}
