// app/page.tsx

'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useSearchParams } from 'next/navigation';


export default function HomePage() {
  const router = useRouter();
  const searchParams = useSearchParams();


  useEffect(() => {
    // Redirect based on session existence
    const sessionFromUrl = searchParams.get('session');
    if (sessionFromUrl) {
      router.push(`/dashboard?session=${sessionFromUrl}`);
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