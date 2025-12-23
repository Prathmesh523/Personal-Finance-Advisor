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

  // Update session from URL
  useEffect(() => {
    const sessionFromUrl = searchParams.get('session');
    if (sessionFromUrl && sessionFromUrl !== currentSession) {
      setCurrentSessionState(sessionFromUrl);
      const session = sessions.find(s => s.id === sessionFromUrl);
      if (session) {
        setCurrentSessionMonth(session.month);
      }
    }
  }, [searchParams, sessions]);

  const fetchSessions = async () => {
    try {
      setLoading(true);
      const data = await api.listSessions();
      
      // Filter completed sessions only
      const completed = data.sessions.filter(s => s.status === 'completed');
      setSessions(completed);

      // Set first session as default if none selected
      if (completed.length > 0) {
        const sessionFromUrl = searchParams.get('session');
        const defaultSession = sessionFromUrl || completed[0].id;
        setCurrentSessionState(defaultSession);
        
        const session = completed.find(s => s.id === defaultSession);
        if (session) {
          setCurrentSessionMonth(session.month);
        }

        // Update URL if no session in URL
        if (!sessionFromUrl) {
          router.replace(`${pathname}?session=${defaultSession}`);
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
    
    const session = sessions.find(s => s.id === sessionId);
    if (session) {
      setCurrentSessionMonth(session.month);
    }

    // Update URL
    router.push(`${pathname}?session=${sessionId}`);
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