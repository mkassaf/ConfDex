export interface AuthStatus {
  authenticated: boolean;
  auth_required: boolean;
}

export async function getAuthStatus(): Promise<AuthStatus> {
  const r = await fetch("/api/auth/status");
  if (!r.ok) return { authenticated: true, auth_required: false };
  return r.json();
}
