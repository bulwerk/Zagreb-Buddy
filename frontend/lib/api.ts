import {
  ChatResponse,
  GoogleCalendarCreateRequest,
  GoogleCalendarEventResponse,
  GoogleCalendarUpdateRequest,
  GoogleConnectResponse,
  GoogleMapsRouteResponse,
  Place,
} from './types';

export async function sendMessage(
  message: string,
  conversationId?: string
): Promise<ChatResponse> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30000);

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
      }),
      signal: controller.signal,
    });

    if (!res.ok) {
      const errorBody = await res.text().catch(() => '');
      throw new Error(`Server error ${res.status}: ${errorBody || res.statusText}`);
    }

    return res.json();
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new Error('Request timed out — the agent is taking too long to respond.');
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }
}

function getOrCreateUserId(): string {
  const key = 'zb_user_id';
  const existing = typeof window !== 'undefined' ? localStorage.getItem(key) : null;
  if (existing) return existing;

  const created =
    typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  if (typeof window !== 'undefined') {
    localStorage.setItem(key, created);
  }
  return created;
}

async function googleFetch<T>(path: string, init: RequestInit): Promise<T> {
  const userId = getOrCreateUserId();
  const res = await fetch(path, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      'X-User-ID': userId,
      ...(init.headers ?? {}),
    },
  });

  if (!res.ok) {
    const detail = await res.text().catch(() => '');
    throw new Error(`Google integration error ${res.status}: ${detail || res.statusText}`);
  }
  return res.json();
}

export async function getGoogleConnectUrl(): Promise<GoogleConnectResponse> {
  return googleFetch<GoogleConnectResponse>('/api/google/connect', {
    method: 'GET',
  });
}

export async function completeGoogleOAuth(code: string): Promise<{ connected: boolean }> {
  return googleFetch<{ connected: boolean }>('/api/google/callback', {
    method: 'POST',
    body: JSON.stringify({ code }),
  });
}

export async function buildGoogleRoute(places: Place[]): Promise<GoogleMapsRouteResponse> {
  return googleFetch<GoogleMapsRouteResponse>('/api/google/maps/route', {
    method: 'POST',
    body: JSON.stringify({ places }),
  });
}

export async function createGoogleCalendarEvent(
  payload: GoogleCalendarCreateRequest
): Promise<GoogleCalendarEventResponse> {
  return googleFetch<GoogleCalendarEventResponse>('/api/google/calendar/events', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateGoogleCalendarEvent(
  payload: GoogleCalendarUpdateRequest
): Promise<GoogleCalendarEventResponse> {
  return googleFetch<GoogleCalendarEventResponse>('/api/google/calendar/events', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}
