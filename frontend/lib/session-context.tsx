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

  const fetchSessions = async () => {
    try {
      setLoading(true);
      const data = await api.listSessions();
      
      const completed = data.sessions.filter(s => s.status === 'completed');
      setSessions(completed);

      if (completed.length > 0) {
        // ✅ Check 3 sources (in priority order)
        const urlParams = new URLSearchParams(window.location.search);
        const sessionFromUrl = urlParams.get('session');
        const sessionFromStorage = localStorage.getItem('last_session_id');
        
        let sessionToUse;
        
        // Priority 1: URL has valid session
        if (sessionFromUrl && completed.find(s => s.id === sessionFromUrl)) {
          sessionToUse = sessionFromUrl;
        } 
        // Priority 2: localStorage has valid session
        else if (sessionFromStorage && completed.find(s => s.id === sessionFromStorage)) {
          sessionToUse = sessionFromStorage;
        } 
        // Priority 3: First session
        else {
          sessionToUse = completed[0].id;
        }
        
        // ✅ Save to localStorage
        localStorage.setItem('last_session_id', sessionToUse);
        
        // Set state
        setCurrentSessionState(sessionToUse);
        const session = completed.find(s => s.id === sessionToUse);
        if (session) {
          setCurrentSessionMonth(session.month);
        }
        
        // Sync URL
        const currentParams = new URLSearchParams(window.location.search);
        const urlSession = currentParams.get('session');
        
        if (urlSession !== sessionToUse) {
          currentParams.set('session', sessionToUse);
          router.replace(`${pathname}?${currentParams.toString()}`);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sessions');
    } finally {
      setLoading(false);
    }
  };

  const setCurrentSession = (sessionId: string) => {
    setCurrentSessionState(sessionId);
    
    // ✅ Save to localStorage
    localStorage.setItem('last_session_id', sessionId);
    
    const session = sessions.find(s => s.id === sessionId);
    if (session) {
      setCurrentSessionMonth(session.month);
    }

    // Preserve other query params
    const currentParams = new URLSearchParams(window.location.search);
    currentParams.set('session', sessionId);
    
    router.push(`${pathname}?${currentParams.toString()}`);
  };

  return (
    <SessionContext.Provider
      value={{
        sessions,
        currentSession,
        currentSessionMonth,
        setCurrentSession,
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