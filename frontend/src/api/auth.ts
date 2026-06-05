export interface AuthStatus {
  authenticated: boolean;
  auth_required: boolean;
}

export async function getAuthStatus(): Promise<AuthStatus> {
  const r = await fetch("/api/auth/status");
  if (!r.ok) return { authenticated: true, auth_required: false };
  return r.json();
}

export async function logout(): Promise<void> {
  // Using fetch() (not a link navigation) is intentional: fetch() does NOT send
  // browser-stored Basic Auth credentials, so the server sees the session cookie only.
  // Once the server revokes it, subsequent fetch() calls return unauthenticated.
  await fetch("/api/auth/logout");
}
