export class AuthError extends Error {
  constructor() {
    super("auth");
    this.code = 401;
  }
}

export class LoginError extends Error {
  constructor(message) {
    super(message);
    this.name = "LoginError";
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

export async function login(username, password) {
  const response = await fetch("/api/auth/login", {
    method: "POST",
    credentials: "include",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  const data = await response.json().catch(() => ({}));
  if (response.status === 401 || response.status === 429 || response.status === 503) {
    const detail = typeof data.detail === "string" ? data.detail : "No se pudo iniciar sesión.";
    throw new LoginError(detail);
  }
  if (!response.ok) throw new Error("request");
  return data;
}

export function logout() {
  return fetch("/api/auth/logout", {
    method: "POST",
    credentials: "include",
    headers: { Accept: "application/json" },
  });
}

export function getCalificados(reelId, { limit = 50, offset = 0 } = {}) {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  return request(`/api/reels/${reelId}/calificados?${params.toString()}`);
}
