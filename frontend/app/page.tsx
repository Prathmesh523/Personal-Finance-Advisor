// app/page.tsx

'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { storage } from '@/lib/storage';

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    // Redirect based on session existence
    const sessionId = storage.getSessionId();
    
    if (sessionId) {
      router.push('/dashboard');
    } else {
      router.push('/upload');
    }
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
    </div>
  );
}