import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Sidebar } from '@/components/Sidebar';
import { SessionProvider } from '@/lib/session-context';
import { SessionSelector } from '@/components/SessionSelector';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Personal Finance Advisor',
  description: 'AI-powered financial reconciliation and analytics',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <SessionProvider>  {/* ✅ WRAP EVERYTHING INCLUDING FIXED SIDEBAR */}
          <div className="flex min-h-screen">
            {/* Fixed Sidebar */}
            <div className="fixed left-0 top-0 h-screen w-64">
              <Sidebar />
            </div>
            
            {/* Main Content */}
            <main className="flex-1 ml-64 bg-gray-50">
              {/* Global header with session selector */}
              <div className="sticky top-0 z-10 bg-white border-b border-gray-200 px-8 py-4">
                <SessionSelector />
              </div>
              {children}
            </main>
          </div>
        </SessionProvider>
      </body>
    </html>
  );
}