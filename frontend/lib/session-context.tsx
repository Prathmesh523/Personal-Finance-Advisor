'use client';

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { api } from './api';
import { useRouter, usePathname, useSearchParams } from 'next/navigation';

interface Session {
  id: string;
  month: string;
  status: string;
  transaction_count: number;
  created_at: string;
}

interface SessionContextType {
  sessions: Session[];
  currentSession: string | null;
  currentSessionMonth: string | null;
  setCurrentSession: (sessionId: string) => void;
  refetchSessions: () => Promise<void>;
  loading: boolean;
  error: string | null;
}

const SessionContext = createContext<SessionContextType | undefined>(undefined);

export function SessionProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSession, setCurrentSessionState] = useState<string | null>(null);
  const [currentSessionMonth, setCurrentSessionMonth] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch available sessions on mount
  useEffect(() => {
    fetchSessions();
  }, []);

  // ✅ SEPARATED: This only fetches sessions, doesn't set current session
  const fetchSessions = async () => {
    console.log('🔄 fetchSessions called');
    try {
      setLoading(true);
      const data = await api.listSessions();
      console.log('   📥 Received sessions:', data.sessions);
      
      const completed = data.sessions.filter(s => s.status === 'completed');
      setSessions(completed);
      console.log('   ✅ Set sessions state:', completed);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sessions');
    } finally {
      setLoading(false);
    }
  };

  // ✅ NEW: Separate useEffect that watches URL and sets current session
  useEffect(() => {
    if (sessions.length === 0) return;
    
    console.log('🔄 URL/sessions changed, updating current session');
    console.log('   Current URL:', window.location.href);
    
    const sessionFromUrl = searchParams.get('session');
    console.log('   Session from URL:', sessionFromUrl);
    
    let sessionToUse;
    
    // Priority 1: URL has valid session
    if (sessionFromUrl && sessions.find(s => s.id === sessionFromUrl)) {
      sessionToUse = sessionFromUrl;
      console.log('   ✅ Using session from URL:', sessionToUse);
    } 
    // Priority 2: First session (fallback)
    else {
      sessionToUse = sessions[0].id;
      console.log('   ⚠️  No valid URL session, using first:', sessionToUse);
    }
    
    // Update state
    setCurrentSessionState(sessionToUse);
    const session = sessions.find(s => s.id === sessionToUse);
    if (session) {
      setCurrentSessionMonth(session.month);
      console.log('   📅 Set month to:', session.month);
    }
    
    // Sync URL if needed
    const currentParams = new URLSearchParams(window.location.search);
    if (currentParams.get('session') !== sessionToUse) {
      currentParams.set('session', sessionToUse);
      console.log('   🔗 Syncing URL to:', sessionToUse);
      router.replace(`${pathname}?${currentParams.toString()}`);
    }
  }, [sessions, searchParams, pathname, router]);

  const setCurrentSession = (sessionId: string) => {
    console.log('🔧 setCurrentSession called with:', sessionId);
    
    setCurrentSessionState(sessionId);
    
    const session = sessions.find(s => s.id === sessionId);
    if (session) {
      setCurrentSessionMonth(session.month);
      console.log('   📅 Set month to:', session.month);
    }

    // Update URL (this will trigger the useEffect above)
    const currentParams = new URLSearchParams(window.location.search);
    currentParams.set('session', sessionId);
    
    console.log('   🔗 Navigating to:', `${pathname}?${currentParams.toString()}`);
    router.push(`${pathname}?${currentParams.toString()}`);
  };

  return (
    <SessionContext.Provider
      value={{
        sessions,
        currentSession,
        currentSessionMonth,
        setCurrentSession,
        refetchSessions: fetchSessions,
        loading,
        error,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error('useSession must be used within SessionProvider');
  }
  return context;
}