// components/Sidebar.tsx

'use client';

import { useRouter, usePathname } from 'next/navigation';
import { storage } from '@/lib/storage';
import { Button } from '@/components/ui/button';
import { LayoutDashboard, Receipt, GitCompare, Upload } from 'lucide-react';
import { useEffect, useState } from 'react'; // ✅ ADD THIS

export function Sidebar() {
  const router = useRouter();
  const pathname = usePathname();
  
  // ✅ FIX: Use state to avoid hydration mismatch
  const [hasSession, setHasSession] = useState(false);

  // ✅ FIX: Check session only on client side
  useEffect(() => {
    setHasSession(storage.getSessionId() !== null);
  }, []);

  const handleNewAnalysis = () => {
    if (confirm('Start a new analysis? This will clear the current session.')) {
      storage.clearSessionId();
      router.push('/upload');
    }
  };

  const isActive = (path: string) => pathname === path;

  const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/transactions', label: 'Transactions', icon: Receipt },
    { path: '/compare', label: 'Compare', icon: GitCompare },
  ];

  return (
    <div className="w-64 bg-gray-900 text-white min-h-screen flex flex-col">
      {/* Logo/Title */}
      <div className="p-6 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <div className="text-3xl">💰</div>
          <div>
            <h1 className="text-xl font-bold">Finance Advisor</h1>
            <p className="text-xs text-gray-400">Smart reconciliation</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      {hasSession ? (
        <nav className="flex-1 p-4 space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.path}
                onClick={() => router.push(item.path)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                  isActive(item.path)
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-300 hover:bg-gray-800'
                }`}
              >
                <Icon className="w-5 h-5" />
                <span className="font-medium">{item.label}</span>
              </button>
            );
          })}
        </nav>
      ) : (
        <div className="flex-1 p-4">
          <p className="text-gray-400 text-sm text-center">
            Upload data to get started
          </p>
        </div>
      )}

      {/* Bottom Actions */}
      <div className="p-4 border-t border-gray-800 space-y-2">
        {hasSession && (
          <Button
            variant="outline"
            className="w-full bg-transparent border-gray-700 text-gray-300 hover:bg-gray-800 hover:text-white"
            onClick={handleNewAnalysis}
          >
            <Upload className="w-4 h-4 mr-2" />
            New Analysis
          </Button>
        )}
      </div>
    </div>
  );
}