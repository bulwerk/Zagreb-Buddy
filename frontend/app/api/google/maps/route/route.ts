import { NextRequest, NextResponse } from 'next/server';

const AGENT_URL = process.env.AGENT_VPS_URL || 'http://localhost:8000';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const userId = req.headers.get('x-user-id');
    if (!userId) {
      return NextResponse.json(
        { error: 'Missing X-User-ID header' },
        { status: 400 }
      );
    }

    const agentRes = await fetch(`${AGENT_URL}/integrations/google/maps/route`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-ID': userId,
      },
      body: JSON.stringify(body),
    });

    const text = await agentRes.text();
    if (!agentRes.ok) {
      return NextResponse.json(
        { error: 'Google maps route failed', detail: text },
        { status: agentRes.status }
      );
    }

    return new NextResponse(text, {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('Google maps route proxy error:', error);
    return NextResponse.json(
      { error: 'Failed to build Google Maps route' },
      { status: 500 }
    );
  }
}
