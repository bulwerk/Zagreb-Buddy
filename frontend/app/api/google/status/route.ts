import { NextResponse } from 'next/server';

const AGENT_URL = process.env.AGENT_VPS_URL || 'http://localhost:8000';

export async function GET(req: Request) {
  const userId = req.headers.get('x-user-id');
  if (!userId) {
    return NextResponse.json({ error: 'Missing X-User-ID header' }, { status: 400 });
  }

  try {
    const response = await fetch(`${AGENT_URL}/integrations/google/status`, {
      method: 'GET',
      headers: {
        'X-User-ID': userId,
      },
    });

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      return NextResponse.json(payload, { status: response.status });
    }
    return NextResponse.json(payload);
  } catch {
    return NextResponse.json({ error: 'Failed to reach agent' }, { status: 500 });
  }
}
