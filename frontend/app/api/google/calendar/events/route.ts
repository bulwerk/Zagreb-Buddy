import { NextRequest, NextResponse } from 'next/server';

const AGENT_URL = process.env.AGENT_VPS_URL || 'http://localhost:8000';

function buildHeaders(req: NextRequest): Record<string, string> {
  const userId = req.headers.get('x-user-id') || '';
  return {
    'Content-Type': 'application/json',
    'X-User-ID': userId,
  };
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const headers = buildHeaders(req);
    const agentRes = await fetch(`${AGENT_URL}/integrations/google/calendar/events`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });

    const data = await agentRes.json().catch(() => ({}));
    if (!agentRes.ok) {
      return NextResponse.json(
        { error: 'Google calendar create failed', detail: data },
        { status: agentRes.status }
      );
    }

    return NextResponse.json(data);
  } catch (err) {
    console.error('Google calendar create proxy error:', err);
    return NextResponse.json(
      { error: 'Failed to proxy Google calendar create' },
      { status: 500 }
    );
  }
}

export async function PATCH(req: NextRequest) {
  try {
    const body = await req.json();
    const headers = buildHeaders(req);
    const agentRes = await fetch(`${AGENT_URL}/integrations/google/calendar/events`, {
      method: 'PATCH',
      headers,
      body: JSON.stringify(body),
    });

    const data = await agentRes.json().catch(() => ({}));
    if (!agentRes.ok) {
      return NextResponse.json(
        { error: 'Google calendar update failed', detail: data },
        { status: agentRes.status }
      );
    }

    return NextResponse.json(data);
  } catch (err) {
    console.error('Google calendar update proxy error:', err);
    return NextResponse.json(
      { error: 'Failed to proxy Google calendar update' },
      { status: 500 }
    );
  }
}
