import { NextRequest, NextResponse } from 'next/server';

const AGENT_URL = process.env.AGENT_VPS_URL || 'http://localhost:8000';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const userId = req.headers.get('x-user-id');
    if (!userId) {
      return NextResponse.json({ error: 'Missing X-User-ID header' }, { status: 400 });
    }

    const upstream = await fetch(`${AGENT_URL}/integrations/google/callback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-ID': userId,
      },
      body: JSON.stringify(body),
    });

    const data = await upstream.json().catch(() => ({}));
    if (!upstream.ok) {
      return NextResponse.json(
        { error: 'Google OAuth callback failed', detail: data },
        { status: upstream.status }
      );
    }

    return NextResponse.json(data);
  } catch (err) {
    console.error('Google callback proxy error:', err);
    return NextResponse.json({ error: 'Failed to complete Google OAuth' }, { status: 500 });
  }
}
