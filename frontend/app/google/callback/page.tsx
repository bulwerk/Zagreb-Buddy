'use client';

import { Suspense, useEffect, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { completeGoogleOAuth } from '@/lib/api';

function GoogleCallbackInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<'working' | 'success' | 'error'>('working');
  const [message, setMessage] = useState('Finishing Google connection...');

  const code = useMemo(() => searchParams.get('code'), [searchParams]);

  useEffect(() => {
    const run = async () => {
      if (!code) {
        setStatus('error');
        setMessage('Missing Google authorization code.');
        return;
      }

      try {
        await completeGoogleOAuth(code);
        setStatus('success');
        setMessage('Google account connected successfully. Redirecting...');
        setTimeout(() => router.push('/'), 1400);
      } catch (err) {
        console.error(err);
        setStatus('error');
        setMessage('Could not connect Google account. Please try again.');
      }
    };

    void run();
  }, [code, router]);

  return (
    <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-6 space-y-3">
      <h1 className="text-lg font-semibold">Google Integration</h1>
      <p className="text-sm text-slate-300">{message}</p>
      {status !== 'working' && (
        <button
          className="mt-2 text-sm px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 transition-colors"
          onClick={() => router.push('/')}
        >
          Back to chat
        </button>
      )}
    </div>
  );
}

function CallbackFallback() {
  return (
    <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-6 space-y-3">
      <h1 className="text-lg font-semibold">Google Integration</h1>
      <p className="text-sm text-slate-300">Finishing Google connection...</p>
    </div>
  );
}

export default function GoogleCallbackPage() {
  return (
    <main className="min-h-[100dvh] bg-slate-950 text-white flex items-center justify-center px-4">
      <Suspense fallback={<CallbackFallback />}>
        <GoogleCallbackInner />
      </Suspense>
    </main>
  );
}
