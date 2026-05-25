export type FitlioSession = {
  token: string;
  memberId: string;
  fullName: string;
  role: string;
};

const TOKEN_KEY = "fitlio_token";
const MEMBER_ID_KEY = "fitlio_member_id";
const USERNAME_KEY = "fitlio_username";
const ROLE_KEY = "fitlio_role";

export const SESSION_CHANGED_EVENT = "fitlio:session-changed";

export function notifySessionChanged(): void {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(SESSION_CHANGED_EVENT));
  }
}

function readLegacy(key: string, legacyKey: string): string {
  if (typeof window === "undefined") {
    return "";
  }
  return window.localStorage.getItem(key) ?? window.localStorage.getItem(legacyKey) ?? "";
}

export function readSession(): FitlioSession | null {
  if (typeof window === "undefined") {
    return null;
  }
  const token = readLegacy(TOKEN_KEY, "token");
  const memberId = readLegacy(MEMBER_ID_KEY, "member_id");
  if (!token || !memberId) {
    return null;
  }
  return {
    token,
    memberId,
    fullName: window.localStorage.getItem(USERNAME_KEY) ?? "",
    role: window.localStorage.getItem(ROLE_KEY) ?? "member"
  };
}

export function writeSession(session: FitlioSession): void {
  window.localStorage.setItem(TOKEN_KEY, session.token);
  window.localStorage.setItem("token", session.token);
  window.localStorage.setItem(MEMBER_ID_KEY, session.memberId);
  window.localStorage.setItem("member_id", session.memberId);
  window.localStorage.setItem(USERNAME_KEY, session.fullName);
  window.localStorage.setItem(ROLE_KEY, session.role);
  notifySessionChanged();
}

export function clearSession(): void {
  for (const key of [TOKEN_KEY, "token", MEMBER_ID_KEY, "member_id", USERNAME_KEY, ROLE_KEY]) {
    window.localStorage.removeItem(key);
  }
  notifySessionChanged();
}

export function getAuthToken(): string {
  return readSession()?.token ?? "";
}

export function getMemberId(): string {
  return readSession()?.memberId ?? "";
}
